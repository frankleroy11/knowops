"""Authorization rules: who may read or write which knowledge base.

`AUTH_MODE=off` keeps the historical single-user behaviour: every request is the
local administrator. Any other value enforces bearer tokens, so an unauthenticated
request fails closed with 401 instead of silently falling back.
"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.auth.models import KB_ROLES, ROLES, ApiToken, KbMember, User
from app.modules.auth.principal import ADMIN, LOCAL_ADMIN, Principal
from app.modules.auth.security import generate_token, hash_token
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


def active_token_count(db: Session, user_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(ApiToken)
            .where(ApiToken.user_id == user_id, ApiToken.revoked_at.is_(None))
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


def issue_token(db: Session, user: User, label: str = "") -> str:
    raw = generate_token()
    db.add(ApiToken(user_id=user.id, token_hash=hash_token(raw), label=label.strip()))
    db.commit()
    return raw


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
    member = db.scalar(
        select(KbMember).where(KbMember.kb_id == kb_id, KbMember.user_id == user_id)
    )
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
    kb = db.get(KnowledgeBase, kb_id)
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
    member = db.scalar(
        select(KbMember).where(KbMember.kb_id == kb_id, KbMember.user_id == user_id)
    )
    if member is None:
        raise HTTPException(404, "该用户不是此知识库成员")
    if member.role == "owner" and owner_count(db, kb_id) <= 1:
        raise HTTPException(409, "知识库至少保留一个 owner")
    db.delete(member)
    db.commit()
