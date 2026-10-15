"""P2: submit → review → publish, audit trail, version publish and retire."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.adapters.vectorstore.milvus import collection_name
from app.core.config import Settings
from app.db.deps import get_db
from app.db.session import Base
from app.main import app
from app.modules.audit.models import AuditLog
from app.modules.auth import service
from app.modules.auth.models import ApiToken, KbMember, User
from app.modules.auth.security import hash_token
from app.modules.knowledge.models import (
    Chunk,
    Document,
    DocumentVersion,
    KnowledgeBase,
    VectorIndex,
)
from app.modules.tenant.models import Tenant

ENFORCED = Settings(auth_mode="enforced")
TOKENS = {"admin": "admin-token", "editor": "editor-token", "alice": "alice-token", "bob": "bob-token"}


def auth(name):
    return {"Authorization": f"Bearer {TOKENS[name]}"}


@pytest.fixture
def db_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'review.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory.begin() as db:
        db.add(Tenant(id=1, name="默认租户", slug="default"))
        db.add(KnowledgeBase(id=1, name="IT", tenant_id=1, review_required=False))
        db.add(KnowledgeBase(id=2, name="HR", tenant_id=1, review_required=True))
        for doc_id, kb_id, filename, content in [
            (1, 1, "vpn.md", "连接 VPN"),
            (2, 2, "leave.md", "年假 5 天"),
        ]:
            db.add(Document(id=doc_id, knowledge_base_id=kb_id, filename=filename))
            db.add(
                DocumentVersion(
                    id=doc_id,
                    document_id=doc_id,
                    version=1,
                    content_hash=str(doc_id) * 64,
                    storage_path=filename,
                    status="parsed",
                    review_status="approved",
                    is_current=True,
                )
            )
            db.add(Chunk(id=doc_id, version_id=doc_id, position=0, content=content))
            db.add(
                VectorIndex(
                    version_id=doc_id,
                    collection=collection_name(),
                    status="indexed",
                    chunks_indexed=1,
                )
            )
        db.add_all(
            [
                User(id=1, email="admin@corp", display_name="Admin", role="admin", tenant_id=None),
                User(id=2, email="editor@corp", display_name="Editor", role="editor", tenant_id=1),
                User(id=3, email="alice@corp", display_name="Alice", role="viewer", tenant_id=1),
                User(id=4, email="bob@corp", display_name="Bob", role="viewer", tenant_id=1),
            ]
        )
        db.add_all(
            [
                ApiToken(id=index, user_id=index, token_hash=hash_token(raw), label="")
                for index, raw in enumerate(TOKENS.values(), start=1)
            ]
        )
        db.add_all(
            [
                KbMember(id=1, kb_id=1, user_id=2, role="owner"),
                KbMember(id=2, kb_id=2, user_id=2, role="editor"),
                KbMember(id=3, kb_id=1, user_id=3, role="viewer"),
                KbMember(id=4, kb_id=2, user_id=4, role="viewer"),
            ]
        )
    return factory


@pytest.fixture
def client(db_factory):
    def database():
        with db_factory() as db:
            yield db

    app.dependency_overrides[get_db] = database
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def enforced():
    with patch.object(service, "get_settings", return_value=ENFORCED):
        yield


def run_search(client, name, kb_id, chunk_ids):
    from app.modules.retrieval import router as retrieval

    class Store:
        def search(self, vector, kb, limit, **kwargs):
            return [{"chunk_id": c, "distance": 0.9 - i / 100} for i, c in enumerate(chunk_ids)]

        def close(self):
            pass

    class Embedder:
        def encode(self, texts, **kwargs):
            return [[1.0, 0.0]]

    with (
        patch.object(retrieval, "MilvusStore", Store),
        patch.object(retrieval, "get_embedder", return_value=Embedder()),
    ):
        return client.post(
            "/api/v1/search",
            json={"query": "VPN", "knowledge_base_id": kb_id},
            headers=auth(name),
        ).json()["hits"]


def upload(client, name, kb_id, filename=b"vpn-v2.md", tmp=None):
    from app.modules.knowledge import router as knowledge

    with (
        patch.object(knowledge, "ROOT", tmp),
        patch.object(knowledge, "dispatch", return_value={"queued": False, "task_id": None}),
    ):
        return client.post(
            f"/api/v1/knowledge-bases/{kb_id}/documents",
            files={"file": ("vpn-v2.md", filename, "text/markdown")},
            headers=auth(name),
        )


def complete_version(db_factory, version_id, texts):
    """Simulate parse + index so the retrieval gate can be exercised."""
    with db_factory.begin() as db:
        db.get(DocumentVersion, version_id).status = "parsed"
        for position, text in enumerate(texts):
            db.add(Chunk(version_id=version_id, position=position, content=text))
        db.add(
            VectorIndex(
                version_id=version_id,
                collection=collection_name(),
                status="indexed",
                chunks_indexed=len(texts),
            )
        )


def chunk_ids_of(db_factory, version_id):
    with db_factory() as db:
        return list(
            db.scalars(
                select(Chunk.id).where(Chunk.version_id == version_id).order_by(Chunk.position)
            )
        )


def audit_actions(db_factory):
    with db_factory() as db:
        return [entry.action for entry in db.scalars(select(AuditLog).order_by(AuditLog.id))]


def test_default_upload_publishes_immediately(client, enforced, db_factory, tmp_path):
    response = upload(client, "editor", 1, tmp=tmp_path)
    assert response.status_code == 202
    assert response.json()["review_status"] == "approved"
    assert response.json()["is_current"] is True
    assert "document.upload" in audit_actions(db_factory)


def test_review_required_upload_waits_and_is_invisible(client, enforced, db_factory, tmp_path):
    response = upload(client, "editor", 2, tmp=tmp_path)
    assert response.json()["review_status"] == "pending"
    assert response.json()["is_current"] is False
    version_id = response.json()["version_id"]
    complete_version(db_factory, version_id, ["新的年假规则"])
    pending_chunk = chunk_ids_of(db_factory, version_id)[0]

    assert run_search(client, "bob", 2, [pending_chunk]) == []
    queue = client.get("/api/v1/knowledge-bases/2/reviews", headers=auth("editor")).json()
    assert [row["version_id"] for row in queue] == [version_id]

    assert (
        client.post(
            f"/api/v1/document-versions/{version_id}/review",
            json={"decision": "approve", "note": "ok"},
            headers=auth("admin"),
        ).status_code
        == 200
    )
    hits = run_search(client, "bob", 2, [pending_chunk])
    assert [hit["chunk_id"] for hit in hits] == [pending_chunk]
    assert "version.approve" in audit_actions(db_factory)


def test_submitter_cannot_approve_own_version(client, enforced, db_factory, tmp_path):
    version_id = upload(client, "editor", 2, tmp=tmp_path).json()["version_id"]
    response = client.post(
        f"/api/v1/document-versions/{version_id}/review",
        json={"decision": "approve"},
        headers=auth("editor"),
    )
    assert response.status_code == 409


def test_rejection_keeps_version_out(client, enforced, db_factory, tmp_path):
    version_id = upload(client, "editor", 2, tmp=tmp_path).json()["version_id"]
    complete_version(db_factory, version_id, ["被驳回的内容"])
    chunk = chunk_ids_of(db_factory, version_id)[0]
    rejected = client.post(
        f"/api/v1/document-versions/{version_id}/review",
        json={"decision": "reject", "note": "口径不符"},
        headers=auth("admin"),
    )
    assert rejected.status_code == 200
    assert rejected.json()["review_status"] == "rejected"
    assert rejected.json()["is_current"] is False
    assert run_search(client, "bob", 2, [chunk]) == []
    assert "version.reject" in audit_actions(db_factory)


def test_new_version_replaces_current_on_publish(client, enforced, db_factory, tmp_path):
    from app.modules.knowledge import router as knowledge

    with (
        patch.object(knowledge, "ROOT", tmp_path),
        patch.object(knowledge, "dispatch", return_value={"queued": False, "task_id": None}),
    ):
        response = client.post(
            "/api/v1/documents/1/versions",
            files={"file": ("vpn-v2.md", b"new vpn policy", "text/markdown")},
            headers=auth("editor"),
        )
    assert response.status_code == 202
    assert response.json()["version"] == 2
    assert response.json()["is_current"] is True
    new_version = response.json()["version_id"]
    complete_version(db_factory, new_version, ["新版 VPN 需要审批"])
    new_chunk = chunk_ids_of(db_factory, new_version)[0]

    with db_factory() as db:
        assert db.get(DocumentVersion, 1).is_current is False
        assert db.get(DocumentVersion, new_version).is_current is True
    hits = run_search(client, "alice", 1, [1, new_chunk])
    assert [hit["chunk_id"] for hit in hits] == [new_chunk]


def test_pending_new_version_keeps_previous_live(client, enforced, db_factory, tmp_path):
    from app.modules.knowledge import router as knowledge

    with (
        patch.object(knowledge, "ROOT", tmp_path),
        patch.object(knowledge, "dispatch", return_value={"queued": False, "task_id": None}),
    ):
        response = client.post(
            "/api/v1/documents/2/versions",
            files={"file": ("leave-v2.md", b"new leave policy", "text/markdown")},
            headers=auth("editor"),
        )
    assert response.json()["review_status"] == "pending"
    with db_factory() as db:
        assert db.get(DocumentVersion, 2).is_current is True
    assert [hit["chunk_id"] for hit in run_search(client, "bob", 2, [2])] == [2]


def test_retire_removes_document_from_retrieval(client, enforced, db_factory):
    response = client.post("/api/v1/documents/1/retire", headers=auth("editor"))
    assert response.status_code == 200 and response.json()["retired_at"]
    with db_factory() as db:
        assert db.get(DocumentVersion, 1).is_current is False
        assert db.get(Document, 1).retired_at is not None
    assert run_search(client, "alice", 1, [1]) == []
    listing = client.get("/api/v1/knowledge-bases/1/documents", headers=auth("editor")).json()
    assert listing[0]["retired_at"] is not None and listing[0]["is_current"] is False
    assert "document.retire" in audit_actions(db_factory)


def test_review_and_retire_require_write_access(client, enforced):
    assert client.get("/api/v1/knowledge-bases/2/reviews", headers=auth("bob")).status_code == 403
    assert (
        client.post(
            "/api/v1/document-versions/2/review", json={"decision": "approve"}, headers=auth("bob")
        ).status_code
        == 403
    )
    assert client.post("/api/v1/documents/2/retire", headers=auth("bob")).status_code == 403
    assert client.get("/api/v1/knowledge-bases/2/reviews", headers=auth("alice")).status_code == 403


def test_audit_log_endpoint_is_admin_only_and_filterable(client, enforced, db_factory):
    client.post("/api/v1/knowledge-bases/1/members", json={"email": "bob@corp"}, headers=auth("editor"))
    assert client.get("/api/v1/admin/audit-logs", headers=auth("editor")).status_code == 403
    everything = client.get("/api/v1/admin/audit-logs", headers=auth("admin")).json()
    assert {"kb.member.grant"} <= {row["action"] for row in everything}
    filtered = client.get(
        "/api/v1/admin/audit-logs?action=kb.member.grant&object_type=knowledge_base",
        headers=auth("admin"),
    ).json()
    assert [row["action"] for row in filtered] == ["kb.member.grant"]
    assert filtered[0]["actor_email"] == "editor@corp"
    assert filtered[0]["object_id"] == 1


def test_kb_update_toggles_review_and_is_audited(client, enforced, db_factory):
    response = client.patch(
        "/api/v1/knowledge-bases/1", json={"review_required": True}, headers=auth("editor")
    )
    assert response.status_code == 200 and response.json()["review_required"] is True
    assert "kb.update" in audit_actions(db_factory)
    assert (
        client.patch(
            "/api/v1/knowledge-bases/1", json={"review_required": False}, headers=auth("alice")
        ).status_code
        == 403
    )


def test_user_management_is_audited(client, enforced, db_factory):
    created = client.post(
        "/api/v1/admin/users", json={"email": "new@corp", "role": "viewer"}, headers=auth("admin")
    ).json()
    client.post(f"/api/v1/admin/users/{created['id']}/tokens", headers=auth("admin"))
    client.delete(f"/api/v1/admin/users/{created['id']}/tokens", headers=auth("admin"))
    actions = audit_actions(db_factory)
    assert {"user.create", "token.issue", "token.revoke"} <= set(actions)
