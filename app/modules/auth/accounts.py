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


# 公开注册：只创建全新的演示空间，不接受客户端指定角色或已有租户。
def register(db, email, password, display_name, ip):
    if not service.get_settings().public_registration_enabled:
        raise HTTPException(403, "当前未开放注册")
    # 注册也占用来源 IP 的限流额度；即使之后登录成功，也不能抹掉注册计数。
    service.enforce_ip_rate_limit(db, ip)
    service.record_login_attempt(db, "registration@" + ip, ip)
    email = email.strip().lower()
    service.validate_password(password, user=User(email=email))
    if service.find_user_by_email(db, email):
        raise HTTPException(409, "该邮箱已注册，请直接登录")
    suffix = uuid4().hex[:16]
    # role=admin 仅表示本空间管理员；tenant_id 非空，所以不是平台管理员。
    tenant = Tenant(name=f"{display_name}的演示空间-{suffix}", slug="demo-" + suffix)
    try:
        db.add(tenant)
        # flush 取得空间主键，但不提交，账号创建失败时仍能回滚空间。
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
        # audit.record 会提交：空间、账号和注册审计在这里一起落库。
        audit.record(db, user, "user.register", "user", user.id, "public demo registration")
    except IntegrityError:
        # 预查邮箱不能消除并发竞争，最终由数据库唯一约束兜底并回滚。
        db.rollback()
        raise HTTPException(409, "该邮箱已注册，请直接登录") from None
    return user


def update(db, principal, user_id, changes):
    # 按固定顺序锁定启用管理员，串行化“移除最后一个管理员”的并发操作。
    # populate_existing 强制刷新会话缓存，避免使用此前读取的旧权限状态。
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
    # 先计算并验证最终状态，全部通过后才修改对象，避免半次更新。
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
        # 只统计同一空间的其他管理员；平台级账号的 tenant_id 同为 None。
        peers = [u for u in admins if u.id != user.id and u.tenant_id == user.tenant_id]
        if not peers:
            raise HTTPException(409, "当前空间至少保留一个启用的管理员")
    changed = (role, active, tenant_id) != (user.role, user.is_active, user.tenant_id)
    if tenant_id != user.tenant_id:
        # 转移空间后旧成员关系必须删除，避免以后移回时旧权限自动恢复。
        for membership in db.scalars(select(KbMember).where(KbMember.user_id == user.id)):
            db.delete(membership)
    user.role, user.is_active, user.tenant_id = role, active, tenant_id
    if "display_name" in changes:
        user.display_name = changes["display_name"].strip() or user.email
    if changed:
        # 权限/启停/空间改变后吊销旧会话；重新启用不会让旧 Token 复活。
        # 单纯修改显示名不影响登录会话。
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
