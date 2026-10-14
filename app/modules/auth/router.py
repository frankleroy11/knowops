"""Current-identity endpoint and administrator user management."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.deps import DB
from app.modules.audit import service as audit
from app.modules.auth import service
from app.modules.auth.deps import AdminPrincipal, CurrentPrincipal
from app.modules.auth.models import User
from app.modules.tenant import service as tenants

router = APIRouter(tags=["认证与用户管理"])

Role = Literal["admin", "editor", "viewer"]


class MeOut(BaseModel):
    id: int | None
    email: str
    display_name: str
    role: str
    tenant_id: int | None
    is_platform_admin: bool
    local: bool
    is_admin: bool
    can_author: bool


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    tenant_id: int | None
    is_active: bool
    active_tokens: int


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: Role = "viewer"
    display_name: str = Field(default="", max_length=128)
    tenant_id: int | None = None
    issue_token: bool = False


class UserCreated(UserOut):
    token: str | None = None


class UserPatch(BaseModel):
    role: Role | None = None
    is_active: bool | None = None
    tenant_id: int | None = None


class TokenOut(BaseModel):
    user_id: int
    token: str
    label: str = ""


def user_out(db, user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
        active_tokens=service.active_token_count(db, user.id),
    )


def get_user(db, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    return user


def resolve_tenant_id(db, principal, requested: int | None) -> int | None:
    """Tenant admins may only act inside their own tenant; platform admins choose."""
    tenant_id = requested if principal.is_platform_admin else principal.tenant_id
    if tenant_id is not None:
        tenants.get_tenant(db, tenant_id)
    return tenant_id


@router.get("/auth/me", response_model=MeOut)
def me(principal: CurrentPrincipal):
    """In AUTH_MODE=off this returns the local administrator without a token,
    which is how the UI knows it may skip the login screen."""
    return MeOut(
        id=principal.id,
        email=principal.email,
        display_name=principal.display_name,
        role=principal.role,
        tenant_id=principal.tenant_id,
        is_platform_admin=principal.is_platform_admin,
        local=principal.local,
        is_admin=principal.is_admin,
        can_author=principal.can_author,
    )


@router.get("/admin/users", response_model=list[UserOut])
def list_users(db: DB, principal: AdminPrincipal):
    users = service.list_users(db)
    if not principal.is_platform_admin:
        users = [user for user in users if user.tenant_id == principal.tenant_id]
    return [user_out(db, user) for user in users]


@router.post("/admin/users", response_model=UserCreated, status_code=201)
def create_user(body: UserCreate, db: DB, principal: AdminPrincipal):
    tenant_id = resolve_tenant_id(db, principal, body.tenant_id)
    user = service.create_user(db, body.email, body.role, body.display_name, tenant_id)
    raw = service.issue_token(db, user, "admin-api") if body.issue_token else None
    audit.record(
        db,
        principal,
        "user.create",
        "user",
        user.id,
        f"role={user.role} tenant={tenant_id} token={bool(raw)}",
    )
    return UserCreated(**user_out(db, user).model_dump(), token=raw)


@router.patch("/admin/users/{user_id}", response_model=UserOut)
def patch_user(user_id: int, body: UserPatch, db: DB, principal: AdminPrincipal):
    user = get_user(db, user_id)
    if not principal.is_platform_admin and user.tenant_id != principal.tenant_id:
        raise HTTPException(404, "用户不存在")
    demoting_self = user.id == principal.id and (
        (body.role is not None and body.role != "admin") or body.is_active is False
    )
    if demoting_self:
        raise HTTPException(409, "不能降低或停用当前登录的管理员自己")
    changes = []
    if body.role is not None:
        changes.append(f"role={service.set_user_role(db, user, body.role).role}")
    if body.is_active is not None:
        changes.append(f"is_active={service.set_user_active(db, user, body.is_active).is_active}")
    if "tenant_id" in body.model_fields_set:
        if not principal.is_platform_admin:
            raise HTTPException(403, "只有平台管理员可以调整用户所属租户")
        target = body.tenant_id
        if target is not None:
            tenants.get_tenant(db, target)
        changes.append(f"tenant={service.set_user_tenant(db, user, target).tenant_id}")
    audit.record(db, principal, "user.update", "user", user.id, " ".join(changes) or "no-change")
    return user_out(db, user)


@router.post("/admin/users/{user_id}/tokens", response_model=TokenOut, status_code=201)
def issue_token(user_id: int, db: DB, principal: AdminPrincipal, label: str = ""):
    user = get_user(db, user_id)
    if not principal.is_platform_admin and user.tenant_id != principal.tenant_id:
        raise HTTPException(404, "用户不存在")
    raw = service.issue_token(db, user, label)
    audit.record(db, principal, "token.issue", "user", user.id, f"label={label}"[:512])
    return TokenOut(user_id=user.id, token=raw, label=label)


@router.delete("/admin/users/{user_id}/tokens")
def revoke_tokens(user_id: int, db: DB, principal: AdminPrincipal):
    user = get_user(db, user_id)
    if not principal.is_platform_admin and user.tenant_id != principal.tenant_id:
        raise HTTPException(404, "用户不存在")
    revoked = service.revoke_tokens(db, user)
    audit.record(db, principal, "token.revoke", "user", user.id, f"revoked={revoked}")
    return {"user_id": user.id, "revoked": revoked}
