"""P3a: tenant isolation for knowledge bases, users and retrieval."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
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
TOKENS = {
    "platform": "platform-token",  # admin, no tenant -> cross-tenant authority
    "t1admin": "t1admin-token",  # admin inside tenant 1
    "t1user": "t1user-token",  # viewer in tenant 1, member of KB 1
    "t2user": "t2user-token",  # viewer in tenant 2, member of KB 2
    "t2editor": "t2editor-token",  # editor in tenant 2, member of KB 2
}


def auth(name):
    return {"Authorization": f"Bearer {TOKENS[name]}"}


@pytest.fixture
def db_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'tenants.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory.begin() as db:
        db.add_all(
            [
                Tenant(id=1, name="默认租户", slug="default"),
                Tenant(id=2, name="Acme 公司", slug="acme"),
            ]
        )
        db.add(KnowledgeBase(id=1, name="IT-1", tenant_id=1))
        db.add(KnowledgeBase(id=2, name="IT-2", tenant_id=2))
        for doc_id, kb_id, filename in [(1, 1, "a1.md"), (2, 2, "a2.md")]:
            db.add(Document(id=doc_id, knowledge_base_id=kb_id, filename=filename))
            db.add(
                DocumentVersion(
                    id=doc_id,
                    document_id=doc_id,
                    version=1,
                    content_hash=str(doc_id) * 64,
                    storage_path=filename,
                    status="parsed",
                )
            )
            db.add(Chunk(id=doc_id, version_id=doc_id, position=0, content="内容"))
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
                User(id=1, email="platform@corp", role="admin", tenant_id=None),
                User(id=2, email="t1admin@corp", role="admin", tenant_id=1),
                User(id=3, email="t1user@corp", role="viewer", tenant_id=1),
                User(id=4, email="t2user@corp", role="viewer", tenant_id=2),
                User(id=5, email="t2editor@corp", role="editor", tenant_id=2),
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
                KbMember(id=1, kb_id=1, user_id=3, role="viewer"),
                KbMember(id=2, kb_id=2, user_id=4, role="viewer"),
                KbMember(id=3, kb_id=2, user_id=5, role="owner"),
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


def run_search(client, name, scope=None, kb_id=None):
    from app.modules.retrieval import router as retrieval

    class Store:
        def search(self, vector, kb, limit):
            return [{"chunk_id": 1, "distance": 0.9}, {"chunk_id": 2, "distance": 0.8}]

        def close(self):
            pass

    class Embedder:
        def encode(self, texts, **kwargs):
            return [[1.0, 0.0]]

    payload = {"query": "VPN", "top_k": 3}
    payload.update(scope or {})
    if kb_id is not None:
        payload["knowledge_base_id"] = kb_id
    with (
        patch.object(retrieval, "MilvusStore", Store),
        patch.object(retrieval, "get_embedder", return_value=Embedder()),
    ):
        return client.post("/api/v1/search", json=payload, headers=auth(name)).json()["hits"]


def test_platform_admin_identity_and_reach(client, enforced):
    me = client.get("/api/v1/auth/me", headers=auth("platform")).json()
    assert me["tenant_id"] is None and me["is_platform_admin"] is True
    assert [kb["id"] for kb in client.get("/api/v1/knowledge-bases", headers=auth("platform")).json()] == [1, 2]
    assert sorted({hit["knowledge_base_id"] for hit in run_search(client, "platform", scope={"scope": "all"})}) == [1, 2]


def test_tenant_admin_is_confined_to_its_tenant(client, enforced):
    me = client.get("/api/v1/auth/me", headers=auth("t1admin")).json()
    assert me["tenant_id"] == 1 and me["is_platform_admin"] is False
    assert [kb["id"] for kb in client.get("/api/v1/knowledge-bases", headers=auth("t1admin")).json()] == [1]
    assert sorted({hit["knowledge_base_id"] for hit in run_search(client, "t1admin", scope={"scope": "all"})}) == [1]


def test_cross_tenant_knowledge_base_is_hidden(client, enforced):
    assert client.post(
        "/api/v1/search", json={"query": "VPN", "knowledge_base_id": 2}, headers=auth("t1user")
    ).status_code == 404
    assert client.get("/api/v1/knowledge-bases/2/documents", headers=auth("t1user")).status_code == 404
    assert client.get("/api/v1/document-versions/2/chunks", headers=auth("t1user")).status_code == 404
    assert client.get("/api/v1/documents/2", headers=auth("t1user")).status_code == 404
    assert client.post("/api/v1/documents/2/retire", headers=auth("t1user")).status_code == 404


def test_same_tenant_non_member_is_403_not_hidden(client, enforced, db_factory):
    with db_factory.begin() as db:
        db.add(User(id=9, email="t1other@corp", role="viewer", tenant_id=1))
        db.add(ApiToken(id=9, user_id=9, token_hash=hash_token("t1other-token"), label=""))
    response = client.post(
        "/api/v1/search",
        json={"query": "VPN", "knowledge_base_id": 1},
        headers={"Authorization": "Bearer t1other-token"},
    )
    assert response.status_code == 403


def test_scope_all_never_crosses_tenants(client, enforced):
    tenant1 = run_search(client, "t1user", scope={"scope": "all"})
    tenant2 = run_search(client, "t2user", scope={"scope": "all"})
    assert {hit["knowledge_base_id"] for hit in tenant1} == {1}
    assert {hit["knowledge_base_id"] for hit in tenant2} == {2}


def test_membership_cannot_cross_tenants(client, enforced):
    denied = client.post(
        "/api/v1/knowledge-bases/1/members",
        json={"email": "t2user@corp", "role": "viewer"},
        headers=auth("t1admin"),
    )
    assert denied.status_code == 404
    allowed = client.post(
        "/api/v1/knowledge-bases/1/members",
        json={"email": "t1user@corp", "role": "editor"},
        headers=auth("t1admin"),
    )
    assert allowed.status_code == 201 and allowed.json()["role"] == "editor"


def test_user_administration_is_tenant_scoped(client, enforced):
    tenant_users = client.get("/api/v1/admin/users", headers=auth("t1admin")).json()
    assert [user["email"] for user in tenant_users] == ["t1admin@corp", "t1user@corp"]
    assert len(client.get("/api/v1/admin/users", headers=auth("platform")).json()) == 5
    assert client.post(
        "/api/v1/admin/users", json={"email": "x@corp"}, headers=auth("t1admin")
    ).json()["tenant_id"] == 1
    assert client.post(
        "/api/v1/admin/users",
        json={"email": "cross@corp", "tenant_id": 2},
        headers=auth("t1admin"),
    ).json()["tenant_id"] == 1
    assert client.post("/api/v1/admin/users/4/tokens", headers=auth("t1admin")).status_code == 404

def test_only_platform_admin_reads_the_audit_trail(client, enforced):
    """Rows are not partitioned per tenant yet, so tenant admins must be refused."""
    assert client.get("/api/v1/admin/audit-logs", headers=auth("t1admin")).status_code == 403
    assert client.get("/api/v1/admin/audit-logs", headers=auth("platform")).status_code == 200


def test_only_platform_admin_manages_tenants(client, enforced, db_factory):
    assert client.get("/api/v1/admin/tenants", headers=auth("t1admin")).status_code == 403
    created = client.post(
        "/api/v1/admin/tenants",
        json={"name": "Globex", "slug": "globex"},
        headers=auth("platform"),
    )
    assert created.status_code == 201 and created.json()["slug"] == "globex"
    with db_factory() as db:
        assert (
            db.scalar(
                select(func.count()).select_from(AuditLog).where(AuditLog.action == "tenant.create")
            )
            == 1
        )
    assert client.post(
        "/api/v1/admin/tenants", json={"name": "Acme 公司", "slug": "acme"}, headers=auth("platform")
    ).status_code == 409


def test_user_tenant_can_only_be_changed_by_platform_admin(client, enforced):
    denied = client.patch(
        "/api/v1/admin/users/3", json={"tenant_id": 2}, headers=auth("t1admin")
    )
    assert denied.status_code == 403
    moved = client.patch(
        "/api/v1/admin/users/3", json={"tenant_id": 2}, headers=auth("platform")
    )
    assert moved.status_code == 200 and moved.json()["tenant_id"] == 2
    assert client.get("/api/v1/knowledge-bases", headers=auth("t1user")).json() == []


def test_knowledge_base_creation_targets_a_tenant(client, enforced):
    tenant_base = client.post(
        "/api/v1/knowledge-bases", json={"name": "T1 新库"}, headers=auth("t1admin")
    ).json()
    assert tenant_base["tenant_id"] == 1
    explicit = client.post(
        "/api/v1/knowledge-bases",
        json={"name": "Acme 新库", "tenant_id": 2},
        headers=auth("platform"),
    ).json()
    assert explicit["tenant_id"] == 2
    fallback = client.post(
        "/api/v1/knowledge-bases", json={"name": "平台默认库"}, headers=auth("platform")
    ).json()
    assert fallback["tenant_id"] == 1
    assert client.get("/api/v1/knowledge-bases", headers=auth("t2editor")).status_code == 200
