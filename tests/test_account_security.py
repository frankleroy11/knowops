"""Account security: password policy/history, per-IP throttling, TOTP 2FA, reset tokens."""

import base64
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
from app.modules.audit.service import prune as prune_audit
from app.modules.auth import service
from app.modules.auth.models import ApiToken, LoginAttempt, PasswordReset, User
from app.modules.auth.security import hash_password, hash_token, totp_code, totp_uri
from app.modules.knowledge.models import KnowledgeBase
from app.modules.oidc.models import OidcLoginState
from app.modules.oidc.service import prune_login_states
from app.modules.tenant.models import Tenant

ENFORCED = Settings(
    auth_mode="enforced",
    token_ttl_days=30,
    password_min_length=8,
    password_require_mixed=True,
    password_history_size=2,
    login_max_failures=5,
    login_lockout_minutes=15,
    login_attempt_window_minutes=10,
    login_attempts_per_ip=3,
    password_reset_ttl_minutes=30,
    totp_window=1,
    totp_issuer_name="KnowOps",
)
PASSWORD = "Correct-Horse9"

# RFC 6238 附录 B 的测试密钥（ASCII "12345678901234567890" 的 base32）
RFC_SECRET = base64.b32encode(b"12345678901234567890").decode("ascii").rstrip("=")


@pytest.fixture
def db_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'security.db'}")
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
            ]
        )
        db.add(ApiToken(id=1, user_id=1, token_hash=hash_token("admin-token"), label=""))
        db.add(ApiToken(id=2, user_id=2, token_hash=hash_token("bob-token"), label=""))
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


def login(client, email="bob@corp", password=PASSWORD, code=""):
    return client.post(
        "/api/v1/auth/password/login", json={"email": email, "password": password, "code": code}
    )


# ---------- TOTP 正确性 ----------


def test_totp_matches_rfc6238_vectors():
    # RFC 6238 附录 B：SHA1 下 59s / 1111111109s 的 8 位结果，取后 6 位即本实现的输出
    assert totp_code(RFC_SECRET, at=59) == "287082"
    assert totp_code(RFC_SECRET, at=1111111109) == "081804"
    assert totp_code(RFC_SECRET, at=1234567890) == "005924"
    assert totp_uri("ABC", "a@b.c", "KnowOps").startswith("otpauth://totp/")


# ---------- 口令策略与历史 ----------


@pytest.mark.parametrize(
    "bad,reason",
    [
        ("short1", "长度"),
        ("alllettershere", "字母数字"),
        ("bob-secret-1", "邮箱名"),
        ("password123", "常见"),
    ],
)
def test_weak_passwords_are_rejected(client, enforced, bad, reason):
    response = client.post(
        "/api/v1/auth/password",
        json={"current_password": PASSWORD, "new_password": bad},
        headers=bearer("bob-token"),
    )
    assert response.status_code == 422, response.text


def test_password_history_blocks_reuse_and_expires_after_n(client, enforced):
    headers = bearer("bob-token")

    def change(current, new):
        response = client.post(
            "/api/v1/auth/password",
            json={"current_password": current, "new_password": new},
            headers=headers,
        )
        if response.status_code == 200:
            assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
            headers.update(bearer(login(client, password=new).json()["token"]))
        return response

    assert change(PASSWORD, "Second-Pass9").status_code == 200
    # 立刻改回：命中最近 2 条历史
    blocked = change("Second-Pass9", PASSWORD)
    assert blocked.status_code == 422 and "最近" in blocked.json()["detail"]
    # 再改两次后，最早的 PASSWORD 滑出窗口，可以重新使用
    assert change("Second-Pass9", "Third-Pass9").status_code == 200
    assert change("Third-Pass9", "Fourth-Pass9").status_code == 200
    assert change("Fourth-Pass9", PASSWORD).status_code == 200


# ---------- 按 IP 限流 ----------


def test_repeated_failures_from_one_ip_are_throttled(client, enforced, db_factory):
    for _ in range(3):
        assert login(client, password="Wrong-Pass9").status_code == 401
    # 第 4 次即使在账号级锁定之前，也已被来源 IP 限流挡住
    throttled = login(client)
    assert throttled.status_code == 429
    assert "该来源" in throttled.json()["detail"]
    with db_factory() as db:
        attempts = list(db.scalars(select(LoginAttempt)))
    assert len(attempts) >= 3
    # 回归：尝试记录也必须用 API 时钟，否则限流窗口比较永远为空
    assert abs((datetime.now() - attempts[-1].created_at).total_seconds()) < 60


def test_successful_login_clears_the_ip_counter(client, enforced, db_factory):
    """内网多人共用一个出口 IP：成功登录后不应继续被上一次的失败拖住。"""
    for _ in range(3):
        assert login(client, password="Wrong-Pass9").status_code == 401
    assert login(client).status_code == 429  # 阈值已到
    with db_factory.begin() as db:
        db.execute(LoginAttempt.__table__.delete())  # 模拟窗口过去
    assert login(client).status_code == 200
    with db_factory() as db:
        assert list(db.scalars(select(LoginAttempt))) == []


# ---------- 二次验证 ----------


def test_totp_enable_login_and_disable(client, enforced):
    setup = client.post("/api/v1/auth/2fa/setup", headers=bearer("bob-token")).json()
    secret = setup["secret"]
    assert setup["otpauth_uri"].startswith("otpauth://totp/")
    assert (
        client.post(
            "/api/v1/auth/2fa/enable", json={"code": "000000"}, headers=bearer("bob-token")
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/2fa/enable", json={"code": totp_code(secret)}, headers=bearer("bob-token")
        ).status_code
        == 200
    )

    missing = login(client)
    assert missing.status_code == 401 and missing.json()["detail"] == "需要二次验证码"
    assert login(client, code="000000").status_code == 401
    ok = login(client, code=totp_code(secret))
    assert ok.status_code == 200 and ok.json()["token"].startswith("knp_")

    me = client.get("/api/v1/auth/me", headers=bearer("bob-token")).json()
    assert me["totp_enabled"] is True
    assert (
        client.post(
            "/api/v1/auth/2fa/disable",
            json={"code": totp_code(secret)},
            headers=bearer("bob-token"),
        ).status_code
        == 200
    )
    assert login(client).status_code == 200


# ---------- 自助重置 ----------


def test_reset_token_flow_is_generic_and_single_use(client, enforced, db_factory):
    unknown = client.post("/api/v1/auth/password/forgot", json={"email": "ghost@corp"})
    known = client.post("/api/v1/auth/password/forgot", json={"email": "bob@corp"})
    assert unknown.status_code == known.status_code == 202
    assert "dev_reset_token" not in known.json()  # 默认不返回令牌

    revealed = ENFORCED.model_copy(update={"auth_dev_reveal_reset_token": True})
    with patch.object(service, "get_settings", return_value=revealed):
        token = client.post("/api/v1/auth/password/forgot", json={"email": "bob@corp"}).json()[
            "dev_reset_token"
        ]

    reset = client.post(
        "/api/v1/auth/password/reset", json={"token": token, "new_password": "Reset-Pass9"}
    )
    assert reset.status_code == 200 and reset.json()["email"] == "bob@corp"
    assert login(client, password=PASSWORD).status_code == 401
    assert login(client, password="Reset-Pass9").status_code == 200
    # 单次使用
    assert (
        client.post(
            "/api/v1/auth/password/reset", json={"token": token, "new_password": "Again-Pass9"}
        ).status_code
        == 400
    )
    # 重置会吊销旧 Token
    assert client.get("/api/v1/auth/me", headers=bearer("bob-token")).status_code == 401


def test_expired_reset_token_is_rejected(client, enforced, db_factory):
    with patch.object(
        service,
        "get_settings",
        return_value=ENFORCED.model_copy(update={"auth_dev_reveal_reset_token": True}),
    ):
        token = client.post("/api/v1/auth/password/forgot", json={"email": "bob@corp"}).json()[
            "dev_reset_token"
        ]
    with db_factory.begin() as db:
        record = db.scalar(select(PasswordReset))
        record.expires_at = datetime.now() - timedelta(minutes=1)
    assert (
        client.post(
            "/api/v1/auth/password/reset", json={"token": token, "new_password": "Later-Pass9"}
        ).status_code
        == 400
    )


# ---------- 登录状态清理与审计导出/保留 ----------


def test_prune_login_states_removes_consumed_and_expired(client, enforced, db_factory):
    with db_factory.begin() as db:
        db.add_all(
            [
                OidcLoginState(state="used", nonce="n", consumed_at=datetime.now()),
                OidcLoginState(
                    state="old", nonce="n", created_at=datetime.now() - timedelta(minutes=30)
                ),
                OidcLoginState(state="fresh", nonce="n", created_at=datetime.now()),
            ]
        )
    with db_factory.begin() as db:
        removed = prune_login_states(db, ttl_minutes=10)
    assert removed == 2
    with db_factory() as db:
        assert [row.state for row in db.scalars(select(OidcLoginState))] == ["fresh"]


def test_audit_export_respects_tenant_and_format(client, enforced, db_factory):
    client.post("/api/v1/knowledge-bases", json={"name": "导出库"}, headers=bearer("admin-token"))
    csv_response = client.get("/api/v1/admin/audit-logs/export", headers=bearer("admin-token"))
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "created_at,actor_email,tenant_id,action" in csv_response.text
    assert "kb.create" in csv_response.text

    json_rows = client.get(
        "/api/v1/admin/audit-logs/export?format=json", headers=bearer("admin-token")
    ).json()
    assert json_rows and json_rows[0]["action"] == "kb.create"
    assert (
        client.get("/api/v1/admin/audit-logs/export", headers=bearer("bob-token")).status_code
        == 403
    )


def test_audit_entries_are_stamped_with_the_api_clock(client, enforced, db_factory):
    """保留策略按 API 时钟比较，所以写入也必须用 API 时钟。"""
    client.post("/api/v1/knowledge-bases", json={"name": "时钟库"}, headers=bearer("admin-token"))
    with db_factory() as db:
        entry = db.scalar(select(AuditLog).order_by(AuditLog.id.desc()))
    assert abs((datetime.now() - entry.created_at).total_seconds()) < 60


def test_audit_retention_deletes_only_old_rows(client, enforced, db_factory):
    with db_factory.begin() as db:
        db.add(
            AuditLog(
                actor_email="a", action="kb.create", created_at=datetime.now() - timedelta(days=400)
            )
        )
        db.add(AuditLog(actor_email="a", action="kb.create", created_at=datetime.now()))
    with db_factory.begin() as db:
        removed = prune_audit(db, datetime.now() - timedelta(days=180))
    assert removed == 1
    with db_factory() as db:
        assert db.scalar(select(AuditLog)).action == "kb.create"


def test_logout_has_no_oidc_hint_for_password_logins(client, enforced):
    token = login(client).json()["token"]
    body = client.post("/api/v1/auth/logout", headers=bearer(token)).json()
    assert body["revoked"] == 1 and body["oidc_logout_url"] is None
