# 中文导读：
# 身份认证与权限业务：解析令牌、检查租户和知识库访问范围、维护密码及二次验证
# 授权必须在后端执行，令牌还需检查有效期与撤销状态

"""Authorization rules: who may read or write which knowledge base.

`AUTH_MODE=off` keeps the historical single-user behaviour: every request is the
local administrator. Any other value enforces bearer tokens, so an unauthenticated
request fails closed with 401 instead of silently falling back.
"""

import secrets
from datetime import datetime, timedelta
from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.audit import service as audit
from app.modules.auth.models import (
    KB_ROLES,
    ROLES,
    ApiToken,
    KbMember,
    LoginAttempt,
    PasswordHistory,
    PasswordReset,
    User,
)
from app.modules.auth.principal import ADMIN, LOCAL_ADMIN, Principal
from app.modules.auth.security import (
    generate_token,
    generate_totp_secret,
    hash_password,
    hash_token,
    verify_password,
    verify_totp,
)
from app.modules.knowledge.models import KnowledgeBase

WRITE_KB_ROLES = ("owner", "editor")
ENFORCED = "enforced"


def auth_mode() -> str:
    return get_settings().auth_mode


def default_principal() -> Principal:
    """Principal for callers that never went through the HTTP dependency."""
    if auth_mode() == ENFORCED:
        raise HTTPException(401, "需要登录")
    return LOCAL_ADMIN


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def resolve_principal(db: Session | None, authorization: str | None) -> Principal:
    if auth_mode() != ENFORCED:
        return LOCAL_ADMIN
    token = _bearer_token(authorization)
    if token is None or db is None:
        raise HTTPException(401, "需要登录")
    record = db.scalar(select(ApiToken).where(ApiToken.token_hash == hash_token(token)))
    if record is None or record.revoked_at is not None:
        raise HTTPException(401, "凭据无效")
    if record.expires_at is not None and record.expires_at <= datetime.now():
        raise HTTPException(401, "凭据已过期，请重新登录")
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(401, "凭据无效")
    record.last_used_at = datetime.now()
    db.commit()
    return Principal(
        id=user.id,
        email=user.email,
        role=user.role,
        display_name=user.display_name,
        tenant_id=user.tenant_id,
    )


def create_user(
    db: Session, email: str, role: str, display_name: str = "", tenant_id: int | None = None
) -> User:
    email = email.strip().lower()
    if role not in ROLES:
        raise HTTPException(422, f"角色必须是 {', '.join(ROLES)}")
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(409, "用户已存在")
    user = User(
        email=email,
        display_name=display_name.strip() or email,
        role=role,
        tenant_id=tenant_id,
    )
    db.add(user)
    db.commit()
    return user


def find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


# 管理页统计“仍可登录”的 Token：同时排除已吊销和已过期的记录。
def active_token_count(db: Session, user_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(ApiToken)
            .where(
                ApiToken.user_id == user_id,
                ApiToken.revoked_at.is_(None),
                or_(ApiToken.expires_at.is_(None), ApiToken.expires_at > datetime.now()),
            )
        )
        or 0
    )


def admin_count(db: Session) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == ADMIN, User.is_active.is_(True))
        )
        or 0
    )


def token_expiry(ttl_days: int | None = None) -> datetime | None:
    """Tokens expire on the API clock, the same clock that verifies them."""
    days = get_settings().token_ttl_days if ttl_days is None else ttl_days
    return datetime.now() + timedelta(days=days) if days else None


def issue_token(
    db: Session,
    user: User,
    label: str = "",
    ttl_days: int | None = None,
    id_token: str | None = None,
) -> str:
    raw = generate_token()
    db.add(
        ApiToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            label=label.strip(),
            expires_at=token_expiry(ttl_days),
            id_token=id_token,
        )
    )
    db.commit()
    return raw


def token_owner(db: Session, authorization: str | None):
    """The user behind the presented token, revoked or not (for audit trails)."""
    raw = _bearer_token(authorization)
    if raw is None:
        return None
    record = db.scalar(select(ApiToken).where(ApiToken.token_hash == hash_token(raw)))
    return db.get(User, record.user_id) if record is not None else None


def revoke_presented_token(db: Session, authorization: str | None) -> int:
    """Logout/rotation: revoke exactly the token that made the request."""
    raw = _bearer_token(authorization)
    if raw is None:
        return 0
    record = db.scalar(select(ApiToken).where(ApiToken.token_hash == hash_token(raw)))
    if record is None or record.revoked_at is not None:
        return 0
    record.revoked_at = datetime.now()
    db.commit()
    return 1


def revoke_tokens(db: Session, user: User) -> int:
    tokens = list(db.scalars(select(ApiToken).where(ApiToken.user_id == user.id)))
    revoked = 0
    for token in tokens:
        if token.revoked_at is None:
            token.revoked_at = datetime.now()
            revoked += 1
    db.commit()
    return revoked


def ensure_membership(db: Session, kb_id: int, user_id: int, role: str) -> KbMember:
    if role not in KB_ROLES:
        raise HTTPException(422, f"知识库角色必须是 {', '.join(KB_ROLES)}")
    member = db.scalar(select(KbMember).where(KbMember.kb_id == kb_id, KbMember.user_id == user_id))
    if member is None:
        member = KbMember(kb_id=kb_id, user_id=user_id, role=role)
        db.add(member)
    else:
        member.role = role
    db.commit()
    return member


def authorized_kb_ids(db: Session, principal: Principal) -> list[int]:
    """Knowledge bases the caller may read; the only source for scope=all.

    Platform admins reach every tenant; tenant members are limited to their own
    tenant even if a stale membership row exists elsewhere.
    """
    if principal.is_platform_admin:
        return list(db.scalars(select(KnowledgeBase.id).order_by(KnowledgeBase.id)))
    if principal.tenant_id is None:
        return []
    if principal.is_admin:
        # A tenant admin administers every knowledge base of their own tenant.
        return list(
            db.scalars(
                select(KnowledgeBase.id)
                .where(KnowledgeBase.tenant_id == principal.tenant_id)
                .order_by(KnowledgeBase.id)
            )
        )
    if principal.id is None:
        return []
    return list(
        db.scalars(
            select(KbMember.kb_id)
            .join(KnowledgeBase, KnowledgeBase.id == KbMember.kb_id)
            .where(
                KbMember.user_id == principal.id,
                KnowledgeBase.tenant_id == principal.tenant_id,
            )
            .order_by(KbMember.kb_id)
        )
    )


def kb_permission(db: Session, principal: Principal, kb_id: int) -> str | None:
    """Return "write", "read" or None when the caller has no access at all."""
    if not has_tenant_access(db, principal, kb_id):
        return None
    if principal.is_admin:
        return "write"
    if principal.id is None:
        return None
    member = db.scalar(
        select(KbMember).where(KbMember.kb_id == kb_id, KbMember.user_id == principal.id)
    )
    if member is None:
        return None
    return "write" if member.role in WRITE_KB_ROLES else "read"


def has_tenant_access(db: Session, principal: Principal, kb_id: int) -> bool:
    """Platform admins reach every tenant; everyone else only their own."""
    if principal.is_platform_admin:
        return True
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        return False
    return principal.tenant_id is not None and kb.tenant_id == principal.tenant_id


def require_kb(db: Session, principal: Principal, kb_id: int, need: str = "read") -> KnowledgeBase:
    """404 when the knowledge base is missing or belongs to another tenant,
    403 when it exists in the caller's tenant but access is missing."""
    kb = (
        db.scalar(select(KnowledgeBase).where(KnowledgeBase.id == kb_id).with_for_update())
        if need == "write"
        else db.get(KnowledgeBase, kb_id)
    )
    if kb is None:
        raise HTTPException(404, "知识库不存在")
    if not has_tenant_access(db, principal, kb_id):
        # Hide cross-tenant existence instead of disclosing it with 403.
        raise HTTPException(404, "知识库不存在")
    granted = kb_permission(db, principal, kb_id)
    if granted is None:
        raise HTTPException(403, "无权访问该知识库")
    if need == "write" and granted != "write":
        raise HTTPException(403, "无权修改该知识库")
    return kb


def require_author(principal: Principal) -> None:
    if not principal.can_author:
        raise HTTPException(403, "需要知识管理员或管理员权限")


def require_admin(principal: Principal) -> None:
    if principal.role != ADMIN:
        raise HTTPException(403, "需要管理员权限")


WEAK_PASSWORDS = frozenset(
    {
        "password",
        "password1",
        "password123",
        "12345678",
        "123456789",
        "qwertyui",
        "qwerty123",
        "abcd1234",
        "admin123",
        "admin12345",
        "knowops123",
    }
)


def validate_password(password: str, user: User | None = None, db: Session | None = None) -> str:
    """口令复杂度 + 历史：长度、字母数字混合、不能是邮箱名、不能是弱口令、不能与最近 N 次重复。"""
    settings = get_settings()
    candidate = password or ""
    if len(candidate) < settings.password_min_length:
        raise HTTPException(422, f"密码至少 {settings.password_min_length} 位")
    if settings.password_require_mixed and not (
        any(ch.isalpha() for ch in candidate) and any(ch.isdigit() for ch in candidate)
    ):
        raise HTTPException(422, "密码需同时包含字母与数字")
    if candidate.lower() in WEAK_PASSWORDS:
        raise HTTPException(422, "密码过于常见，请更换")
    if user is not None:
        local_part = (user.email or "").split("@")[0].lower()
        if local_part and local_part in candidate.lower():
            raise HTTPException(422, "密码不能包含邮箱名")
        if db is not None and settings.password_history_size:
            recent = list(
                db.scalars(
                    select(PasswordHistory.password_hash)
                    .where(PasswordHistory.user_id == user.id)
                    .order_by(PasswordHistory.id.desc())
                    .limit(settings.password_history_size)
                )
            )
            if user.password_hash:
                recent.append(user.password_hash)
            if any(verify_password(candidate, previous) for previous in recent):
                raise HTTPException(
                    422, f"不能使用最近 {settings.password_history_size} 次用过的密码"
                )
    return candidate


def remember_password(db: Session, user: User) -> None:
    """把当前口令摘要记入历史表，并只保留最近 N 条。"""
    if not user.password_hash:
        return
    db.add(PasswordHistory(user_id=user.id, password_hash=user.password_hash))
    db.commit()
    keep = get_settings().password_history_size
    if keep <= 0:
        db.execute(delete(PasswordHistory).where(PasswordHistory.user_id == user.id))
        db.commit()
        return
    stale = list(
        db.scalars(
            select(PasswordHistory)
            .where(PasswordHistory.user_id == user.id)
            .order_by(PasswordHistory.id.desc())
            .offset(keep)
        )
    )
    for row in stale:
        db.delete(row)
    if stale:
        db.commit()


def record_login_attempt(db: Session, email: str, ip: str = "") -> None:
    """记录一次失败尝试，并顺手清掉窗口外的旧记录。"""
    # 用 API 时钟写入：限流窗口也按同一时钟比较（数据库可能是 UTC）
    db.add(
        LoginAttempt(email=(email or "").strip().lower(), ip=ip or "", created_at=datetime.now())
    )
    db.commit()
    window = get_settings().login_attempt_window_minutes
    cutoff = datetime.now() - timedelta(minutes=window * 4)
    db.execute(delete(LoginAttempt).where(LoginAttempt.created_at < cutoff))
    db.commit()


def enforce_ip_rate_limit(db: Session, ip: str) -> None:
    """按来源 IP 限制失败次数：与账号级锁定互补，防撞库。"""
    if not ip:
        return
    settings = get_settings()
    since = datetime.now() - timedelta(minutes=settings.login_attempt_window_minutes)
    failures = (
        db.scalar(
            select(func.count())
            .select_from(LoginAttempt)
            .where(LoginAttempt.ip == ip, LoginAttempt.created_at >= since)
        )
        or 0
    )
    if failures >= settings.login_attempts_per_ip:
        raise HTTPException(429, "该来源登录尝试过于频繁，请稍后再试")


def clear_login_attempts(db: Session, email: str, ip: str = "") -> None:
    """成功登录后清掉该账号的失败记录。

    同时清掉同一来源 IP 的记录：企业内网常见多人共用一个出口 IP，若不清零，
    几次输错口令就会把整个出口锁到窗口结束。取舍是：攻击者若已掌握一个有效账号，
    可通过一次成功登录重置该 IP 的计数——但此时它已不再是"盲撞库"场景。
    """
    # 成功登录仅清除当前账号的失败记录，不能替其他账号清除 IP 限流。
    conditions = [LoginAttempt.email == (email or "").strip().lower()]
    if ip:
        conditions.append(LoginAttempt.ip == ip)
    db.execute(delete(LoginAttempt).where(*conditions))
    db.commit()


# ---- 二次验证（TOTP）----


def start_totp(db: Session, user: User) -> str:
    if user.totp_enabled:
        raise HTTPException(409, "已启用二次验证；如需更换请先停用")
    user.totp_secret = generate_totp_secret()
    db.commit()
    return user.totp_secret


def enable_totp(db: Session, user: User, code: str) -> User:
    if user.totp_enabled:
        raise HTTPException(409, "二次验证已启用")
    if not user.totp_secret:
        raise HTTPException(409, "请先调用 /auth/2fa/setup 获取密钥")
    if not verify_totp(user.totp_secret, code, get_settings().totp_window):
        raise HTTPException(401, "验证码不正确")
    user.totp_enabled = True
    db.commit()
    audit.record(db, user, "user.2fa.enable", "user", user.id, f"email={user.email}")
    return user


def disable_totp(db: Session, user: User, code: str) -> User:
    if not user.totp_enabled:
        raise HTTPException(409, "当前未启用二次验证")
    if not verify_totp(user.totp_secret, code, get_settings().totp_window):
        raise HTTPException(401, "验证码不正确")
    user.totp_enabled = False
    user.totp_secret = None
    db.commit()
    audit.record(db, user, "user.2fa.disable", "user", user.id, f"email={user.email}")
    return user


# ---- 自助重置令牌 ----


def create_reset_token(db: Session, user: User, ttl_minutes: int | None = None) -> str:
    settings = get_settings()
    ttl = settings.password_reset_ttl_minutes if ttl_minutes is None else ttl_minutes
    raw = generate_token()
    db.add(
        PasswordReset(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now() + timedelta(minutes=ttl),
        )
    )
    db.commit()
    audit.record(db, user, "user.password.reset_requested", "user", user.id, f"email={user.email}")
    return raw


def consume_reset_token(db: Session, raw: str, new_password: str) -> User:
    record = db.scalar(select(PasswordReset).where(PasswordReset.token_hash == hash_token(raw)))
    if record is None or record.used_at is not None or record.expires_at <= datetime.now():
        raise HTTPException(400, "重置链接无效或已过期")
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(400, "重置链接无效或已过期")
    record.used_at = datetime.now()
    set_password(db, user, new_password, actor=user)
    # 口令已重置：吊销所有旧 Token，并要求重新登录
    revoke_tokens(db, user)
    audit.record(db, user, "user.password.reset_completed", "user", user.id, f"email={user.email}")
    return user


def set_password(db: Session, user: User, password: str, actor=None) -> User:
    validate_password(password, user=user, db=db)
    remember_password(db, user)
    user.password_hash = hash_password(password)
    # 自助修改和管理员重置共用这条路径，密码更新后统一吊销旧登录凭据。
    for token in db.scalars(
        select(ApiToken).where(ApiToken.user_id == user.id, ApiToken.revoked_at.is_(None))
    ):
        token.revoked_at = datetime.now()
    user.failed_logins = 0
    user.locked_until = None
    db.commit()
    audit.record(
        db,
        actor if actor is not None else user,
        "user.password.set",
        "user",
        user.id,
        f"email={user.email}",
    )
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> User:
    if user.password_hash and not verify_password(current_password, user.password_hash):
        raise HTTPException(401, "当前密码不正确")
    return set_password(db, user, new_password, actor=user)


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    """Keeps unknown-account logins as expensive as real ones."""
    return hash_password(secrets.token_urlsafe(24))


def authenticate_password(
    db: Session, email: str, password: str, code: str | None = None, ip: str = ""
) -> User:
    settings = get_settings()
    enforce_ip_rate_limit(db, ip)
    user = db.scalar(select(User).where(User.email == (email or "").strip().lower()))
    generic = HTTPException(401, "邮箱或密码不正确")
    if user is None:
        verify_password(password, _dummy_password_hash())
        record_login_attempt(db, email, ip)
        raise generic
    if not user.is_active:
        verify_password(password, _dummy_password_hash())
        record_login_attempt(db, email, ip)
        raise generic
    now = datetime.now()
    if user.locked_until is not None and user.locked_until > now:
        minutes = int((user.locked_until - now).total_seconds() // 60) + 1
        raise HTTPException(429, f"登录失败次数过多，请约 {minutes} 分钟后再试")
    if not verify_password(password, user.password_hash):
        user.failed_logins = (user.failed_logins or 0) + 1
        if user.failed_logins >= settings.login_max_failures:
            user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
            user.failed_logins = 0
        db.commit()
        record_login_attempt(db, email, ip)
        raise generic
    if user.totp_enabled:
        if not code:
            raise HTTPException(401, "需要二次验证码")
        if not verify_totp(user.totp_secret, code, settings.totp_window):
            record_login_attempt(db, email, ip)
            raise HTTPException(401, "二次验证码不正确")
    user.failed_logins = 0
    user.locked_until = None
    db.commit()
    clear_login_attempts(db, email, ip)
    return user


def set_user_role(db: Session, user: User, role: str) -> User:
    if role not in ROLES:
        raise HTTPException(422, f"角色必须是 {', '.join(ROLES)}")
    if user.role == ADMIN and role != ADMIN and admin_count(db) <= 1:
        raise HTTPException(409, "至少保留一个启用的管理员")
    user.role = role
    db.commit()
    return user


def set_user_active(db: Session, user: User, is_active: bool) -> User:
    if not is_active and user.role == ADMIN and admin_count(db) <= 1:
        raise HTTPException(409, "至少保留一个启用的管理员")
    user.is_active = is_active
    db.commit()
    return user


def membership_roles(db: Session, principal: Principal) -> dict[int, str]:
    """All knowledge-base roles of the caller in one query, for list rendering."""
    if principal.is_admin or principal.id is None:
        return {}
    return {
        member.kb_id: member.role
        for member in db.scalars(
            select(KbMember)
            .join(KnowledgeBase, KnowledgeBase.id == KbMember.kb_id)
            .where(
                KbMember.user_id == principal.id,
                KnowledgeBase.tenant_id == principal.tenant_id,
            )
        )
    }


def kb_role(db: Session, principal: Principal, kb_id: int) -> str | None:
    """Membership role of the caller ("owner"/"editor"/"viewer"), "admin" for admins."""
    if not has_tenant_access(db, principal, kb_id):
        return None
    if principal.is_admin:
        return ADMIN
    if principal.id is None:
        return None
    member = db.scalar(
        select(KbMember).where(KbMember.kb_id == kb_id, KbMember.user_id == principal.id)
    )
    return member.role if member else None


def set_user_tenant(db: Session, user: User, tenant_id: int | None) -> User:
    """Move a user between tenants; NULL makes the account platform-level."""
    user.tenant_id = tenant_id
    db.commit()
    return user


def list_members(db: Session, kb_id: int) -> list[dict]:
    rows = db.execute(
        select(KbMember, User)
        .join(User, KbMember.user_id == User.id)
        .where(KbMember.kb_id == kb_id)
        .order_by(KbMember.role, User.id)
    ).all()
    return [
        {
            "user_id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": member.role,
        }
        for member, user in rows
    ]


def owner_count(db: Session, kb_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(KbMember)
            .where(KbMember.kb_id == kb_id, KbMember.role == "owner")
        )
        or 0
    )


def remove_membership(db: Session, kb_id: int, user_id: int) -> None:
    member = db.scalar(select(KbMember).where(KbMember.kb_id == kb_id, KbMember.user_id == user_id))
    if member is None:
        raise HTTPException(404, "该用户不是此知识库成员")
    if member.role == "owner" and owner_count(db, kb_id) <= 1:
        raise HTTPException(409, "知识库至少保留一个 owner")
    db.delete(member)
    db.commit()


def presented_token(db: Session, authorization: str | None) -> ApiToken | None:
    raw = _bearer_token(authorization)
    if raw is None:
        return None
    return db.scalar(select(ApiToken).where(ApiToken.token_hash == hash_token(raw)))
