"""P1.5: local password login, login lockout and API-token lifecycle."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.deps import get_db
from app.db.session import Base
from app.main import app
from app.modules.audit.models import AuditLog
from app.modules.auth import service
from app.modules.auth.models import ApiToken, KbMember, User
from app.modules.auth.security import hash_password, hash_token
from app.modules.knowledge.models import KnowledgeBase
from app.modules.tenant.models import Tenant

ENFORCED = Settings(
    auth_mode="enforced",
    token_ttl_days=30,
    password_min_length=8,
    login_max_failures=3,
    login_lockout_minutes=15,
)
PASSWORD = "correct-horse"


@pytest.fixture
def db_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'password.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory.begin() as db:
        db.add(Tenant(id=1, name="默认租户", slug="default"))
        db.add(KnowledgeBase(id=1, name="IT", tenant_id=1))
        db.add_all(
            [
                User(
                    id=1,
                    email="alice@corp",
                    display_name="Alice",
                    role="admin",
                    tenant_id=1,
                    password_hash=hash_password(PASSWORD),
                ),
                User(
                    id=2,
                    email="bob@corp",
                    display_name="Bob",
                    role="viewer",
                    tenant_id=1,
                    password_hash=hash_password(PASSWORD),
                ),
                User(id=3, email="sso@corp", display_name="SSO", role="viewer", tenant_id=1),
                User(id=4, email="other@corp", role="viewer", tenant_id=None),
            ]
        )
        db.add(KbMember(id=1, kb_id=1, user_id=2, role="viewer"))
        db.add(ApiToken(id=1, user_id=1, token_hash=hash_token("admin-token"), label=""))
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


def bearer(raw):
    return {"Authorization": f"Bearer {raw}"}


def login(client, email="bob@corp", password=PASSWORD):
    return client.post("/api/v1/auth/password/login", json={"email": email, "password": password})


def test_password_login_returns_a_working_token(client, enforced):
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token"].startswith("knp_") and body["expires_at"]
    me = client.get("/api/v1/auth/me", headers=bearer(body["token"])).json()
    assert me["email"] == "bob@corp" and me["role"] == "viewer"


def test_password_login_is_audited(client, enforced, db_factory):
    login(client)
    with db_factory() as db:
        actions = [row.action for row in db.scalars(select(AuditLog))]
    assert "auth.password.login" in actions


def test_unknown_email_and_wrong_password_look_identical(client, enforced):
    wrong = login(client, password="nope-nope-nope")
    unknown = login(client, email="ghost@corp", password=PASSWORD)
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"] == "邮箱或密码不正确"


def test_repeated_failures_lock_the_account(client, enforced):
    for _ in range(3):
        assert login(client, password="wrong-wrong").status_code == 401
    locked = login(client)
    assert locked.status_code == 429
    assert "登录失败次数过多" in locked.json()["detail"]


def test_successful_login_clears_failure_counter(client, enforced, db_factory):
    login(client, password="wrong-wrong")
    assert login(client).status_code == 200
    with db_factory() as db:
        user = db.get(User, 2)
        assert (user.failed_logins, user.locked_until) == (0, None)


def test_expired_token_is_rejected_but_fresh_one_works(client, enforced, db_factory):
    issued = login(client).json()["token"]
    with db_factory.begin() as db:
        db.add(
            ApiToken(
                id=9,
                user_id=2,
                token_hash=hash_token("stale-token"),
                label="stale",
                expires_at=datetime.now() - timedelta(minutes=1),
            )
        )
    assert client.get("/api/v1/auth/me", headers=bearer(issued)).status_code == 200
    stale = client.get("/api/v1/auth/me", headers=bearer("stale-token"))
    assert stale.status_code == 401 and "已过期" in stale.json()["detail"]


def test_tokens_can_be_issued_without_expiry(client, enforced, db_factory):
    with db_factory() as db:
        user = db.get(User, 2)
        service.issue_token(db, user, "forever", ttl_days=0)
        record = db.scalar(select(ApiToken).where(ApiToken.label == "forever"))
    assert record.expires_at is None


def test_rotation_invalidates_the_previous_token(client, enforced):
    original = login(client).json()["token"]
    rotated = client.post("/api/v1/auth/token/rotate", headers=bearer(original))
    assert rotated.status_code == 200
    fresh = rotated.json()["token"]
    assert fresh != original
    assert client.get("/api/v1/auth/me", headers=bearer(original)).status_code == 401
    assert client.get("/api/v1/auth/me", headers=bearer(fresh)).status_code == 200


def test_logout_revokes_only_the_presented_token(client, enforced):
    first = login(client).json()["token"]
    second = login(client).json()["token"]
    assert client.post("/api/v1/auth/logout", headers=bearer(first)).json()["revoked"] == 1
    assert client.get("/api/v1/auth/me", headers=bearer(first)).status_code == 401
    assert client.get("/api/v1/auth/me", headers=bearer(second)).status_code == 200
    assert client.post("/api/v1/auth/logout").json()["revoked"] == 0


def test_logout_is_audited(client, enforced, db_factory):
    token = login(client).json()["token"]
    assert client.post("/api/v1/auth/logout", headers=bearer(token)).json()["revoked"] == 1
    with db_factory() as db:
        actions = [row.action for row in db.scalars(select(AuditLog))]
    assert "auth.logout" in actions


def test_change_password_requires_the_current_one(client, enforced):
    token = login(client).json()["token"]
    denied = client.post(
        "/api/v1/auth/password",
        json={"current_password": "not-it", "new_password": "brand-new-pass"},
        headers=bearer(token),
    )
    assert denied.status_code == 401
    changed = client.post(
        "/api/v1/auth/password",
        json={"current_password": PASSWORD, "new_password": "brand-new-pass"},
        headers=bearer(token),
    )
    assert changed.status_code == 200
    assert login(client).status_code == 401
    assert login(client, password="brand-new-pass").status_code == 200


def test_short_passwords_are_rejected(client, enforced):
    token = login(client).json()["token"]
    response = client.post(
        "/api/v1/auth/password",
        json={"current_password": PASSWORD, "new_password": "short"},
        headers=bearer(token),
    )
    assert response.status_code == 422


def test_admin_can_reset_a_password_inside_its_tenant(client, enforced, db_factory):
    reset = client.post(
        "/api/v1/admin/users/2/password",
        json={"password": "reset-by-admin"},
        headers=bearer("admin-token"),
    )
    assert reset.status_code == 200
    assert login(client, password="reset-by-admin").status_code == 200
    assert login(client).status_code == 401


def test_password_login_is_unavailable_in_local_mode(client, db_factory):
    with patch.object(service, "get_settings", return_value=Settings(auth_mode="off")):
        assert client.post(
            "/api/v1/auth/password/login", json={"email": "bob@corp", "password": PASSWORD}
        ).status_code == 404


def test_accounts_without_a_password_cannot_log_in(client, enforced):
    response = login(client, email="sso@corp")
    assert response.status_code == 401
