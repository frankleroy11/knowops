"""P0 authorization: authentication, 401/403 semantics and knowledge-base scoping."""

import hashlib
from datetime import datetime
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

ENFORCED = Settings(auth_mode="enforced")
TOKENS = {
    "alice": "alice-token",  # viewer, member of KB 1
    "bob": "bob-token",  # viewer, member of KB 2
    "admin": "admin-token",  # global admin, no membership row
    "editor": "editor-token",  # editor, owner of KB 1
}


def auth(name):
    return {"Authorization": f"Bearer {TOKENS[name]}"}


@pytest.fixture
def db_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'authz.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory.begin() as db:
        db.add_all([KnowledgeBase(id=1, name="IT"), KnowledgeBase(id=2, name="HR")])
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
                User(id=1, email="alice@corp", display_name="Alice", role="viewer"),
                User(id=2, email="bob@corp", display_name="Bob", role="viewer"),
                User(id=3, email="admin@corp", display_name="Admin", role="admin"),
                User(id=4, email="editor@corp", display_name="Editor", role="editor"),
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
                KbMember(id=1, kb_id=1, user_id=1, role="viewer"),
                KbMember(id=2, kb_id=2, user_id=2, role="viewer"),
                KbMember(id=3, kb_id=1, user_id=4, role="owner"),
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


class Store:
    def __init__(self, seen):
        self.seen = seen

    def search(self, vector, kb_id, limit):
        self.seen["kb_id"] = kb_id
        return [{"chunk_id": 1, "distance": 0.9}, {"chunk_id": 2, "distance": 0.8}]

    def close(self):
        pass


class Embedder:
    def encode(self, texts, **kwargs):
        return [[1.0, 0.0]]


def run_search(client, payload, name, seen):
    from app.modules.retrieval import router as retrieval

    with (
        patch.object(retrieval, "MilvusStore", lambda: Store(seen)),
        patch.object(retrieval, "get_embedder", return_value=Embedder()),
    ):
        return client.post("/api/v1/search", json=payload, headers=auth(name))


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("post", "/api/v1/search", {"query": "VPN", "knowledge_base_id": 1}),
        ("get", "/api/v1/knowledge-bases", None),
        ("post", "/api/v1/chat/ask", {"question": "VPN", "knowledge_base_id": 1}),
    ],
)
def test_enforced_mode_rejects_missing_or_invalid_token(client, enforced, method, path, payload):
    request = getattr(client, method)
    kwargs = {"json": payload} if payload else {}
    assert request(path, **kwargs).status_code == 401
    assert request(path, headers={"Authorization": "Bearer wrong"}, **kwargs).status_code == 401


def test_token_lookup_never_uses_raw_value(db_factory):
    with db_factory() as db:
        token = db.get(ApiToken, 1)
    assert token.token_hash == hashlib.sha256(b"alice-token").hexdigest()
    assert "alice-token" not in token.token_hash


def test_revoked_token_is_rejected(client, enforced, db_factory):
    with db_factory.begin() as db:
        db.get(ApiToken, 1).revoked_at = datetime.now()
    assert client.get("/api/v1/knowledge-bases", headers=auth("alice")).status_code == 401


def test_all_scope_expands_only_to_authorized_kbs(client, enforced):
    seen = {}
    response = run_search(client, {"query": "VPN和年假", "scope": "all"}, "alice", seen)
    assert response.status_code == 200
    assert seen["kb_id"] == [1]
    assert [h["knowledge_base_id"] for h in response.json()["hits"]] == [1]


def test_admin_all_scope_includes_every_kb(client, enforced):
    seen = {}
    response = run_search(client, {"query": "VPN和年假", "scope": "all"}, "admin", seen)
    assert response.status_code == 200
    assert seen["kb_id"] == [1, 2]
    assert [h["knowledge_base_id"] for h in response.json()["hits"]] == [1, 2]


def test_explicit_unauthorized_kb_is_403_not_empty(client, enforced):
    response = client.post(
        "/api/v1/search", json={"query": "年假", "knowledge_base_id": 2}, headers=auth("alice")
    )
    assert response.status_code == 403


def test_chat_ask_rejects_unauthorized_kb(client, enforced):
    response = client.post(
        "/api/v1/chat/ask",
        json={"question": "年假几天", "knowledge_base_id": 2},
        headers=auth("alice"),
    )
    assert response.status_code == 403


def test_kb_and_document_lists_are_filtered_by_membership(client, enforced):
    listing = client.get("/api/v1/knowledge-bases", headers=auth("alice"))
    assert [kb["id"] for kb in listing.json()] == [1]
    assert [
        kb["id"] for kb in client.get("/api/v1/knowledge-bases", headers=auth("admin")).json()
    ] == [1, 2]
    assert client.get("/api/v1/knowledge-bases/2/documents", headers=auth("alice")).status_code == 403
    assert client.get("/api/v1/documents/2", headers=auth("alice")).status_code == 403
    assert (
        client.get("/api/v1/document-versions/2/chunks", headers=auth("alice")).status_code == 403
    )


def test_viewer_cannot_create_kb_or_upload(client, enforced):
    assert (
        client.post(
            "/api/v1/knowledge-bases", json={"name": "违规库"}, headers=auth("alice")
        ).status_code
        == 403
    )
    upload = client.post(
        "/api/v1/knowledge-bases/1/documents",
        files={"file": ("a.md", b"hello", "text/markdown")},
        headers=auth("alice"),
    )
    assert upload.status_code == 403


def test_editor_creates_kb_owned_by_self(client, enforced, db_factory):
    response = client.post(
        "/api/v1/knowledge-bases", json={"name": "新产品库"}, headers=auth("editor")
    )
    assert response.status_code == 201
    kb_id = response.json()["id"]
    with db_factory() as db:
        assert db.get(KnowledgeBase, kb_id).owner_id == 4
        member = db.scalar(
            select(KbMember).where(KbMember.kb_id == kb_id, KbMember.user_id == 4)
        )
        assert member.role == "owner"


def test_owner_upload_records_actor(client, enforced, db_factory, tmp_path):
    from app.modules.knowledge import router as knowledge

    with (
        patch.object(knowledge, "ROOT", tmp_path),
        patch.object(knowledge, "dispatch", return_value={"queued": False, "task_id": None}),
    ):
        response = client.post(
            "/api/v1/knowledge-bases/1/documents",
            files={"file": ("a.md", b"hello", "text/markdown")},
            headers=auth("editor"),
        )
    assert response.status_code == 202
    with db_factory() as db:
        assert db.get(Document, response.json()["document_id"]).uploaded_by == 4


def test_local_mode_still_acts_as_local_admin(client):
    listing = client.get("/api/v1/knowledge-bases")
    assert listing.status_code == 200
    assert [kb["id"] for kb in listing.json()] == [1, 2]
    seen = {}
    assert run_search(client, {"query": "VPN和年假", "scope": "all"}, "alice", seen).status_code == 200
    assert seen["kb_id"] == [1, 2]
