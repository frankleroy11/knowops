# 中文导读：
# 首次创建平台管理员并将生成凭据写入受限本地文件；已有管理员时不重置密码
# 凭据文件不能提交或公开

"""Create the first local platform administrator without printing credentials."""

import json
import os
import secrets

from sqlalchemy import select

from app.core.config import ROOT
from app.db.session import SessionLocal
from app.modules.audit import service as audit
from app.modules.auth.models import User
from app.modules.auth.principal import LOCAL_ADMIN
from app.modules.auth.security import hash_password
from app.modules.knowledge import models  # noqa: F401 - register FK targets


def main():
    target = ROOT / ".tmp/local-admin-credentials.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with SessionLocal.begin() as db:
        existing = db.scalar(
            select(User).where(
                User.role == "admin", User.tenant_id.is_(None), User.is_active.is_(True)
            )
        )
        if existing:
            print("An active platform administrator already exists; no credential was changed.")
            return
        if target.exists():
            raise RuntimeError(
                "Credential file already exists; review it before bootstrapping again"
            )
        password = "Aa1!" + secrets.token_urlsafe(24)
        user = User(
            email="admin@knowops.local",
            display_name="本地平台管理员",
            role="admin",
            password_hash=hash_password(password),
        )
        db.add(user)
        db.flush()
        # Write before committing so disk errors cannot create an inaccessible admin.
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"email": user.email, "password": password}, f, ensure_ascii=False, indent=2)
        try:
            audit.record(
                db, LOCAL_ADMIN, "user.bootstrap", "user", user.id, "first platform administrator"
            )
        except Exception:
            target.unlink(missing_ok=True)
            raise
    print("Administrator created. Read credentials locally:", target)


if __name__ == "__main__":
    main()
