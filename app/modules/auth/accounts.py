"""Public demo registration and transactional account administration."""

from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.audit import service as audit
from app.modules.auth import service
from app.modules.auth.models import ApiToken, KbMember, User
from app.modules.auth.security import hash_password
from app.modules.tenant.models import Tenant


def register(db, email, password, display_name, ip):
    if not service.get_settings().public_registration_enabled:
        raise HTTPException(403, "当前未开放注册")
    service.enforce_ip_rate_limit(db, ip)
    service.record_login_attempt(db, "registration@" + ip, ip)
    email = email.strip().lower()
    service.validate_password(password, user=User(email=email))
    if service.find_user_by_email(db, email):
        raise HTTPException(409, "该邮箱已注册，请直接登录")
    suffix = uuid4().hex[:16]
    tenant = Tenant(name=f"{display_name}的演示空间-{suffix}", slug="demo-" + suffix)
    try:
        db.add(tenant)
        db.flush()
        user = User(
            email=email,
            display_name=display_name,
            role="admin",
            tenant_id=tenant.id,
            password_hash=hash_password(password),
        )
        db.add(user)
        db.flush()
        audit.record(db, user, "user.register", "user", user.id, "public demo registration")
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "该邮箱已注册，请直接登录") from None
    return user


def update(db, principal, user_id, changes):
    # Serialize admin removals, including simultaneous attempts on the last two.
    admins = list(
        db.scalars(
            select(User)
            .where(User.role == "admin", User.is_active.is_(True))
            .order_by(User.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    user = db.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user is None or (not principal.is_platform_admin and user.tenant_id != principal.tenant_id):
        raise HTTPException(404, "用户不存在")
    if "tenant_id" in changes and not principal.is_platform_admin:
        raise HTTPException(403, "只有平台管理员可以调整用户所属空间")
    role = changes.get("role", user.role)
    active = changes.get("is_active", user.is_active)
    tenant_id = changes.get("tenant_id", user.tenant_id)
    if role is None or active is None:
        raise HTTPException(422, "角色和启用状态不能为空")
    if tenant_id is not None and db.get(Tenant, tenant_id) is None:
        raise HTTPException(404, "租户不存在")
    if principal.id == user_id and (role != user.role or not active or tenant_id != user.tenant_id):
        raise HTTPException(409, "不能降低、停用或转移当前登录的管理员自己")
    if (
        user.role == "admin"
        and user.is_active
        and (role != "admin" or not active or tenant_id != user.tenant_id)
    ):
        peers = [u for u in admins if u.id != user.id and u.tenant_id == user.tenant_id]
        if not peers:
            raise HTTPException(409, "当前空间至少保留一个启用的管理员")
    changed = (role, active, tenant_id) != (user.role, user.is_active, user.tenant_id)
    if tenant_id != user.tenant_id:
        # Membership must be granted afresh in the new space, not resurrected later.
        for membership in db.scalars(select(KbMember).where(KbMember.user_id == user.id)):
            db.delete(membership)
    user.role, user.is_active, user.tenant_id = role, active, tenant_id
    if "display_name" in changes:
        user.display_name = changes["display_name"].strip() or user.email
    if changed:
        for token in db.scalars(
            select(ApiToken).where(ApiToken.user_id == user.id, ApiToken.revoked_at.is_(None))
        ):
            token.revoked_at = datetime.now()
    audit.record(
        db,
        principal,
        "user.update",
        "user",
        user.id,
        f"role={role} active={active} tenant={tenant_id}",
    )
    return user
