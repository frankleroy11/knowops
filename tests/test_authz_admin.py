"""P1: current identity, administrator user management and KB member management."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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
from app.modules.tenant.models import Tenant

ENFORCED = Settings(auth_mode="enforced")
TOKENS = {"alice": "alice-token", "bob": "bob-token", "admin": "admin-token", "editor": "editor-token"}


def auth(name):
    return {"Authorization": f"Bearer {TOKENS[name]}"}


@pytest.fixture
def db_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'admin.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory.begin() as db:
        db.add(Tenant(id=1, name="默认租户", slug="default"))
        db.add_all([KnowledgeBase(id=1, name="IT", tenant_id=1), KnowledgeBase(id=2, name="HR", tenant_id=1)])
        for doc_id, kb_id, filename in [(1, 1, "vpn.md"), (2, 2, "leave.md")]:
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
                User(id=1, email="alice@corp", display_name="Alice", role="viewer", tenant_id=1),
                User(id=2, email="bob@corp", display_name="Bob", role="viewer", tenant_id=1),
                User(id=3, email="admin@corp", display_name="Admin", role="admin", tenant_id=1),
                User(id=4, email="editor@corp", display_name="Editor", role="editor", tenant_id=1),
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


def test_auth_me_reports_local_admin_without_token(client):
    body = client.get("/api/v1/auth/me").json()
    assert body["local"] is True and body["is_admin"] is True and body["can_author"] is True
    assert body["email"] == "local@localhost" and body["id"] is None


def test_auth_me_requires_token_in_enforced_mode(client, enforced):
    with patch.object(service, "get_settings", return_value=ENFORCED):
        assert client.get("/api/v1/auth/me").status_code == 401
        body = client.get("/api/v1/auth/me", headers=auth("alice")).json()
    assert body == {
        "id": 1,
        "email": "alice@corp",
        "display_name": "Alice",
        "role": "viewer",
        "tenant_id": 1,
        "is_platform_admin": False,
        "local": False,
        "is_admin": False,
        "can_author": False,
    }


def test_only_admin_manages_users(client, enforced):
    assert client.get("/api/v1/admin/users", headers=auth("alice")).status_code == 403
    assert (
        client.post(
            "/api/v1/admin/users", json={"email": "x@corp"}, headers=auth("editor")
        ).status_code
        == 403
    )
    listing = client.get("/api/v1/admin/users", headers=auth("admin"))
    assert listing.status_code == 200
    assert [user["email"] for user in listing.json()] == [
        "alice@corp",
        "bob@corp",
        "admin@corp",
        "editor@corp",
    ]
    assert listing.json()[0]["active_tokens"] == 1


def test_created_user_token_authenticates_immediately(client, enforced):
    created = client.post(
        "/api/v1/admin/users",
        json={"email": "new@corp", "role": "editor", "issue_token": True},
        headers=auth("admin"),
    )
    assert created.status_code == 201
    token = created.json()["token"]
    assert token.startswith("knp_")
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["email"] == "new@corp" and me["can_author"] is True
    assert client.get("/api/v1/knowledge-bases", headers={"Authorization": f"Bearer {token}"}).json() == []
    assert (
        client.post(
            "/api/v1/admin/users", json={"email": "new@corp"}, headers=auth("admin")
        ).status_code
        == 409
    )


def test_issue_and_revoke_tokens(client, enforced):
    issued = client.post("/api/v1/admin/users/1/tokens?label=laptop", headers=auth("admin"))
    assert issued.status_code == 201
    token = issued.json()["token"]
    assert client.get("/api/v1/knowledge-bases", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    revoked = client.delete("/api/v1/admin/users/1/tokens", headers=auth("admin"))
    assert revoked.json()["revoked"] == 2
    assert client.get("/api/v1/knowledge-bases", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.get("/api/v1/knowledge-bases", headers=auth("alice")).status_code == 401


def test_admin_cannot_demote_or_deactivate_self(client, enforced):
    assert (
        client.patch("/api/v1/admin/users/3", json={"role": "viewer"}, headers=auth("admin")).status_code
        == 409
    )
    assert (
        client.patch(
            "/api/v1/admin/users/3", json={"is_active": False}, headers=auth("admin")
        ).status_code
        == 409
    )


def test_last_active_admin_is_protected(client, enforced, db_factory):
    from fastapi import HTTPException

    with db_factory() as db:
        admin = db.get(User, 3)
        with pytest.raises(HTTPException) as error:
            service.set_user_role(db, admin, "viewer")
        assert error.value.status_code == 409
        service.create_user(db, "admin2@corp", "admin", tenant_id=1)
        assert service.set_user_role(db, admin, "viewer").role == "viewer"


def test_kb_list_exposes_caller_role(client, enforced):
    mine = client.get("/api/v1/knowledge-bases", headers=auth("alice")).json()
    assert [(kb["id"], kb["my_role"]) for kb in mine] == [(1, "viewer")]
    everything = client.get("/api/v1/knowledge-bases", headers=auth("admin")).json()
    assert [(kb["id"], kb["my_role"]) for kb in everything] == [(1, "admin"), (2, "admin")]


def test_editor_kb_is_owned_by_creator(client, enforced):
    created = client.post(
        "/api/v1/knowledge-bases", json={"name": "研发库"}, headers=auth("editor")
    )
    assert created.json()["my_role"] == "owner"
    again = client.get("/api/v1/knowledge-bases", headers=auth("editor")).json()
    assert {(kb["id"], kb["my_role"]) for kb in again} == {(1, "owner"), (created.json()["id"], "owner")}


def test_member_management_requires_kb_write(client, enforced):
    assert client.get("/api/v1/knowledge-bases/1/members", headers=auth("alice")).status_code == 403
    assert (
        client.post(
            "/api/v1/knowledge-bases/1/members",
            json={"email": "bob@corp", "role": "viewer"},
            headers=auth("alice"),
        ).status_code
        == 403
    )
    assert client.get("/api/v1/knowledge-bases/2/members", headers=auth("alice")).status_code == 403


def test_owner_grants_and_revokes_membership(client, enforced):
    listing = client.get("/api/v1/knowledge-bases/1/members", headers=auth("editor"))
    assert listing.status_code == 200
    assert {row["email"] for row in listing.json()} == {"alice@corp", "editor@corp"}
    added = client.post(
        "/api/v1/knowledge-bases/1/members",
        json={"email": "bob@corp", "role": "viewer"},
        headers=auth("editor"),
    )
    assert added.status_code == 201 and added.json()["role"] == "viewer"
    assert client.get("/api/v1/knowledge-bases/1/members", headers=auth("bob")).status_code == 403
    assert client.get("/api/v1/knowledge-bases/1/documents", headers=auth("bob")).status_code == 200
    assert (
        client.delete("/api/v1/knowledge-bases/1/members/2", headers=auth("editor")).status_code == 204
    )
    assert client.get("/api/v1/knowledge-bases/1/documents", headers=auth("bob")).status_code == 403
    assert (
        client.delete("/api/v1/knowledge-bases/1/members/2", headers=auth("editor")).status_code == 404
    )


def test_last_owner_cannot_be_removed(client, enforced):
    assert (
        client.delete("/api/v1/knowledge-bases/1/members/4", headers=auth("editor")).status_code == 409
    )


def test_unknown_member_email_is_404(client, enforced):
    assert (
        client.post(
            "/api/v1/knowledge-bases/1/members",
            json={"email": "ghost@corp", "role": "viewer"},
            headers=auth("editor"),
        ).status_code
        == 404
    )


def test_admin_patch_role_and_activation(client, enforced, db_factory):
    assert (
        client.patch(
            "/api/v1/admin/users/1", json={"role": "editor", "is_active": False}, headers=auth("admin")
        ).status_code
        == 200
    )
    with db_factory() as db:
        alice = db.get(User, 1)
        assert (alice.role, alice.is_active) == ("editor", False)
    assert client.get("/api/v1/knowledge-bases", headers=auth("alice")).status_code == 401
