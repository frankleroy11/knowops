# 中文导读：
# 以临时租户和成员验证公开注册、权限及令牌撤销，涉及真实数据库；清理操作仅限脚本记录的测试对象

"""Real MySQL account acceptance via HTTP TestClient; prepares disposable UI accounts.

No mocks/dependency overrides. Does not alter existing accounts or credentials.
Run --cleanup after UI inspection. Test rate-limit records use a reserved peer IP.
"""

import argparse
import json
import os
import secrets
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.modules.audit.models import AuditLog
from app.modules.auth.models import ApiToken, KbMember, LoginAttempt, PasswordHistory, User
from app.modules.knowledge.models import KnowledgeBase
from app.modules.tenant.models import Tenant

TARGET = Path(".tmp/account-acceptance-private.json")
PEER = "198.18.0.7"


def cleanup():
    data = json.loads(TARGET.read_text())
    with SessionLocal.begin() as db:
        db.execute(delete(KbMember).where(KbMember.user_id.in_(data["user_ids"])))
        db.execute(delete(KnowledgeBase).where(KnowledgeBase.id.in_(data["kb_ids"])))
        db.execute(delete(AuditLog).where(AuditLog.tenant_id.in_(data["tenant_ids"])))
        db.execute(delete(ApiToken).where(ApiToken.user_id.in_(data["user_ids"])))
        db.execute(delete(PasswordHistory).where(PasswordHistory.user_id.in_(data["user_ids"])))
        db.execute(delete(User).where(User.id.in_(data["user_ids"])))
        db.execute(delete(Tenant).where(Tenant.id.in_(data["tenant_ids"])))
        db.execute(delete(LoginAttempt).where(LoginAttempt.ip == PEER))
    TARGET.unlink()
    print("Disposable account acceptance data cleaned; existing accounts preserved")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    if args.cleanup:
        cleanup()
        return
    assert not TARGET.exists(), "Clean previous acceptance accounts first"
    client = TestClient(app, client=(PEER, 50000))
    assert client.get("/api/v1/auth/options").json()["registration_enabled"]
    marker = uuid4().hex[:12]
    password = "Valid!9-" + secrets.token_hex(12)
    data = {"tenant_ids": [], "user_ids": [], "kb_ids": [], "credentials": {}}
    checks = []

    def save():
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(TARGET, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def call(method, path, expected=200, token=None, **kwargs):
        r = client.request(
            method,
            "/api/v1" + path,
            headers={"Authorization": "Bearer " + token} if token else {},
            **kwargs,
        )
        assert r.status_code == expected, f"{method} {path}: HTTP {r.status_code}"
        return r.json()

    def login(email, pwd=password):
        return call("POST", "/auth/password/login", json={"email": email, "password": pwd})["token"]

    try:
        for label in ["a", "b"]:
            email = f"{label}-{marker}@example.invalid"
            call(
                "POST",
                "/auth/register",
                201,
                json={
                    "email": email,
                    "display_name": "演示空间" + label,
                    "password": password,
                    "confirm_password": password,
                },
            )
            token = login(email)
            profile = call("GET", "/auth/me", token=token)
            assert profile["is_admin"] and not profile["is_platform_admin"]
            data["tenant_ids"].append(profile["tenant_id"])
            data["user_ids"].append(profile["id"])
            data["credentials"][label] = {"email": email, "password": password}
            save()
        a = login(data["credentials"]["a"]["email"])
        b = login(data["credentials"]["b"]["email"])
        kb = call("POST", "/knowledge-bases", 201, token=a, json={"name": "账号验收-" + marker})
        data["kb_ids"].append(kb["id"])
        save()
        call("GET", f"/knowledge-bases/{kb['id']}/documents", 404, token=b)
        call("GET", "/admin/system/status", 403, token=a)
        assert len(call("GET", "/admin/users", token=a)) == 1
        checks.append("registration_creates_isolated_tenant_and_denies_cross_tenant_access")
        email = f"member-{marker}@example.invalid"
        member = call(
            "POST",
            "/admin/users",
            201,
            token=a,
            json={"email": email, "role": "viewer", "password": password},
        )
        data["user_ids"].append(member["id"])
        save()
        viewer = login(email)
        call("GET", "/admin/users", 403, token=viewer)
        changed = "Changed!8-" + secrets.token_hex(12)
        call("POST", f"/admin/users/{member['id']}/password", token=a, json={"password": changed})
        call("GET", "/auth/me", 401, token=viewer)
        viewer = login(email, changed)
        call("PATCH", f"/admin/users/{member['id']}", token=a, json={"role": "editor"})
        call("GET", "/auth/me", 401, token=viewer)
        editor = login(email, changed)
        assert call("GET", "/auth/me", token=editor)["role"] == "editor"
        call("PATCH", f"/admin/users/{member['id']}", token=a, json={"is_active": False})
        call("GET", "/auth/me", 401, token=editor)
        call("POST", "/auth/password/login", 401, json={"email": email, "password": changed})
        call("PATCH", f"/admin/users/{member['id']}", token=a, json={"is_active": True})
        call("GET", "/auth/me", 401, token=editor)
        assert (
            len(call("GET", "/admin/users?q=member&role=editor&active=true&limit=1", token=a)) == 1
        )
        call(
            "PATCH", f"/admin/users/{data['user_ids'][0]}", 409, token=a, json={"is_active": False}
        )
        checks.append("member_password_reset_role_change_disable_and_reenable_revoke_sessions")
        checks.append("search_filter_pagination_and_self_admin_guard")
        data["credentials"]["member"] = {"email": email, "password": changed}
        save()
        Path(".tmp/account-acceptance-report.json").write_text(
            json.dumps({"checks": checks, "passed": True}, indent=2)
        )
        print(
            "PASS:", len(checks), "real DB account acceptance groups; disposable UI accounts ready"
        )
    except Exception:
        if TARGET.exists():
            cleanup()
        raise


if __name__ == "__main__":
    main()
