from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.modules.auth import service
from app.modules.auth.models import ApiToken, User
from app.modules.auth.security import hash_token
from app.modules.tenant.models import Tenant
from tests.test_password_auth import client as old_client
from tests.test_password_auth import db_factory as old_factory


@pytest.fixture
def db_factory(tmp_path):
    return old_factory.__wrapped__(tmp_path)


@pytest.fixture
def client(db_factory):
    yield from old_client.__wrapped__(db_factory)


@pytest.fixture(autouse=True)
def enforced():
    with patch.object(
        service,
        "get_settings",
        return_value=Settings(
            auth_mode="enforced", public_registration_enabled=True, login_attempts_per_ip=20
        ),
    ):
        yield


def payload(email="new@example.invalid"):
    return {
        "email": email,
        "display_name": "演示成员",
        "password": "Valid-Pass9!",
        "confirm_password": "Valid-Pass9!",
    }


def auth(raw="admin-token"):
    return {"Authorization": "Bearer " + raw}


def test_public_registration_isolated_and_login(client, db_factory):
    response = client.post("/api/v1/auth/register", json=payload(" New@Example.invalid "))
    assert response.status_code == 201
    session = client.post(
        "/api/v1/auth/password/login",
        json={"email": "new@example.invalid", "password": "Valid-Pass9!"},
    ).json()
    headers = auth(session["token"])
    profile = client.get("/api/v1/auth/me", headers=headers).json()
    assert profile["is_admin"] and not profile["is_platform_admin"] and profile["tenant_id"] != 1
    assert client.get("/api/v1/knowledge-bases", headers=headers).json() == []
    assert client.get("/api/v1/knowledge-bases/1/documents", headers=headers).status_code == 404
    assert client.get("/api/v1/admin/system/status", headers=headers).status_code == 403
    assert len(client.get("/api/v1/admin/users", headers=headers).json()) == 1
    with db_factory() as db:
        user = db.scalar(select(User).where(User.email == "new@example.invalid"))
        assert user.password_hash != "Valid-Pass9!"


@pytest.mark.parametrize(
    "changes,status",
    [
        ({"role": "admin", "tenant_id": 1}, 422),
        ({"confirm_password": "Other-Pass9!"}, 422),
        ({"email": "bad"}, 422),
        ({"password": "password123", "confirm_password": "password123"}, 422),
    ],
)
def test_registration_validation_does_not_create_accounts(client, db_factory, changes, status):
    body = {**payload(), **changes}
    assert client.post("/api/v1/auth/register", json=body).status_code == status
    with db_factory() as db:
        assert db.scalar(select(User).where(User.email == "new@example.invalid")) is None
        assert len(list(db.scalars(select(Tenant)))) == 1


def test_duplicate_and_registration_switch(client):
    assert client.post("/api/v1/auth/register", json=payload()).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload()).status_code == 409
    with patch.object(service.get_settings(), "public_registration_enabled", False):
        assert not client.get("/api/v1/auth/options").json()["registration_enabled"]
        assert (
            client.post("/api/v1/auth/register", json=payload("other@example.invalid")).status_code
            == 403
        )


def test_login_cannot_erase_registration_rate_limit(client):
    with patch.object(service.get_settings(), "login_attempts_per_ip", 2):
        assert client.post("/api/v1/auth/register", json=payload()).status_code == 201
        assert (
            client.post(
                "/api/v1/auth/password/login",
                json={"email": "new@example.invalid", "password": "Valid-Pass9!"},
            ).status_code
            == 200
        )
        assert (
            client.post("/api/v1/auth/register", json=payload("second@example.invalid")).status_code
            == 201
        )
        assert (
            client.post("/api/v1/auth/register", json=payload("third@example.invalid")).status_code
            == 429
        )


def test_patch_is_atomic_and_self_cannot_move(client, db_factory):
    response = client.patch(
        "/api/v1/admin/users/2", headers=auth(), json={"role": "editor", "tenant_id": 999}
    )
    assert response.status_code == 403
    with db_factory() as db:
        assert db.get(User, 2).role == "viewer"
    assert (
        client.patch("/api/v1/admin/users/1", headers=auth(), json={"is_active": False}).status_code
        == 409
    )


def test_password_reset_revokes_old_session_and_search_filters(client):
    r = client.post(
        "/api/v1/admin/users",
        headers=auth(),
        json={"email": "member@example.invalid", "role": "viewer", "password": "Initial-Pass9!"},
    )
    assert r.status_code == 201 and r.json()["password_configured"]
    uid = r.json()["id"]
    session = client.post(
        "/api/v1/auth/password/login",
        json={"email": "member@example.invalid", "password": "Initial-Pass9!"},
    ).json()
    assert (
        client.post(
            f"/api/v1/admin/users/{uid}/password",
            headers=auth(),
            json={"password": "Changed-Pass9!"},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me", headers=auth(session["token"])).status_code == 401
    rows = client.get(
        "/api/v1/admin/users?q=member&role=viewer&active=true&limit=1", headers=auth()
    ).json()
    assert len(rows) == 1 and rows[0]["id"] == uid
    assert client.get("/api/v1/admin/users?q=%25", headers=auth()).json() == []


def test_last_tenant_admin_protected_even_with_platform_admin(client, db_factory):
    with db_factory.begin() as db:
        db.add(User(id=5, email="platform@example.invalid", role="admin"))
        db.add(ApiToken(user_id=5, token_hash=hash_token("platform-token")))
    response = client.patch(
        "/api/v1/admin/users/1", headers=auth("platform-token"), json={"role": "viewer"}
    )
    assert response.status_code == 409
