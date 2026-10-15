"""Current-identity endpoint and administrator user management."""

import re
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.deps import DB
from app.modules.audit import service as audit
from app.modules.auth import service
from app.modules.auth.deps import AdminPrincipal, CurrentPrincipal
from app.modules.auth.models import User
from app.modules.auth.security import totp_uri
from app.modules.oidc import service as oidc_service
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
    totp_enabled: bool = False


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    tenant_id: int | None
    is_active: bool
    active_tokens: int
    password_configured: bool = False
    locked_until: str | None = None


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: Role = "viewer"
    display_name: str = Field(default="", max_length=128)
    tenant_id: int | None = None
    issue_token: bool = False
    password: str | None = Field(default=None, min_length=8, max_length=256)


class UserCreated(UserOut):
    token: str | None = None


class UserPatch(BaseModel):
    display_name: str = Field(default="", max_length=128)
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
        password_configured=bool(user.password_hash),
        locked_until=user.locked_until.isoformat() if user.locked_until else None,
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


def me_totp_enabled(db, principal) -> bool:
    if principal.id is None:
        return False
    user = db.get(User, principal.id)
    return bool(user and user.totp_enabled)


@router.get("/auth/me", response_model=MeOut)
def me(db: DB, principal: CurrentPrincipal):
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
        totp_enabled=me_totp_enabled(db, principal),
    )


class PasswordLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)
    code: str = Field(default="", max_length=16, description="启用二次验证时必填的 TOTP 验证码")


class PasswordChange(BaseModel):
    current_password: str = Field(default="", max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=256)


class SessionOut(BaseModel):
    token: str
    expires_at: str | None
    user: dict


def session_out(user: User, raw: str, expires_at) -> SessionOut:
    return SessionOut(
        token=raw,
        expires_at=expires_at.isoformat() if expires_at else None,
        user={
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
            "tenant_id": user.tenant_id,
        },
    )


def require_realm(feature: str) -> None:
    if service.auth_mode() != service.ENFORCED:
        raise HTTPException(404, f"{feature}仅在 AUTH_MODE=enforced 下可用")


@router.post("/auth/password/login", response_model=SessionOut)
def password_login(body: PasswordLogin, db: DB, request: Request):
    """Local account login: email + password (+ TOTP when enabled) -> API token."""
    require_realm("账号密码登录")
    client_ip = request.client.host if request.client else ""
    user = service.authenticate_password(db, body.email, body.password, body.code, client_ip)
    raw = service.issue_token(db, user, "password")
    audit.record(db, user, "auth.password.login", "user", user.id, f"email={user.email}")
    return session_out(user, raw, service.token_expiry())


@router.post("/auth/password")
def change_password(body: PasswordChange, db: DB, principal: CurrentPrincipal):
    if principal.id is None:
        raise HTTPException(404, "本地免鉴权模式下没有本地账号")
    user = db.get(User, principal.id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    service.change_password(db, user, body.current_password, body.new_password)
    return {"ok": True}


@router.post("/auth/logout")
def logout(db: DB, authorization: Annotated[str | None, Header()] = None):
    """吊销当前 Token；若是 SSO 登录，同时给出带 id_token_hint 的提供方登出地址。"""
    user = service.token_owner(db, authorization)
    oidc_logout_url = oidc_service.logout_url_for_token(db, authorization)
    revoked = service.revoke_presented_token(db, authorization)
    if user is not None and revoked:
        audit.record(db, user, "auth.logout", "user", user.id, f"email={user.email}"[:512])
    return {"revoked": revoked, "oidc_logout_url": oidc_logout_url}


@router.post("/auth/token/rotate", response_model=SessionOut)
def rotate_token(
    db: DB,
    principal: CurrentPrincipal,
    authorization: Annotated[str | None, Header()] = None,
    label: str = "rotated",
):
    """Revoke the presented token and hand back a fresh one."""
    if principal.id is None:
        raise HTTPException(404, "本地免鉴权模式下没有可轮换的 Token")
    user = db.get(User, principal.id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    service.revoke_presented_token(db, authorization)
    raw = service.issue_token(db, user, label)
    audit.record(db, user, "token.rotate", "user", user.id, f"email={user.email}")
    return session_out(user, raw, service.token_expiry())


@router.get("/admin/users", response_model=list[UserOut])
def list_users(
    db: DB,
    principal: AdminPrincipal,
    q: str = "",
    role: Role | None = None,
    active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
):
    from sqlalchemy import or_, select

    query = select(User)
    if not principal.is_platform_admin:
        query = query.where(User.tenant_id == principal.tenant_id)
    if q.strip():
        # Literal substring search, not SQL wildcard search.
        query = query.where(
            or_(
                User.email.contains(q.strip(), autoescape=True),
                User.display_name.contains(q.strip(), autoescape=True),
            )
        )
    if role is not None:
        query = query.where(User.role == role)
    if active is not None:
        query = query.where(User.is_active == active)
    users = db.scalars(
        query.order_by(User.id).offset(max(0, offset)).limit(min(max(1, limit), 100))
    )
    return [user_out(db, user) for user in users]


@router.post("/admin/users", response_model=UserCreated, status_code=201)
def create_user(body: UserCreate, db: DB, principal: AdminPrincipal):
    tenant_id = resolve_tenant_id(db, principal, body.tenant_id)
    if body.password:
        service.validate_password(body.password, user=User(email=body.email.strip().lower()))
    user = service.create_user(db, body.email, body.role, body.display_name, tenant_id)
    if body.password:
        service.set_password(db, user, body.password, actor=principal)
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
    from app.modules.auth import accounts

    user = accounts.update(db, principal, user_id, body.model_dump(exclude_unset=True))
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


class ResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class ResetConfirm(BaseModel):
    token: str = Field(min_length=8, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class TotpCode(BaseModel):
    code: str = Field(min_length=6, max_length=16)


class TotpSetupOut(BaseModel):
    secret: str
    otpauth_uri: str


@router.post("/auth/password/forgot", status_code=202)
def forgot_password(body: ResetRequest, db: DB):
    """自助重置第一步：生成一次性令牌。

    统一返回同样的提示，避免暴露邮箱是否存在。未配置邮件通道时，
    只有在 AUTH_DEV_REVEAL_RESET_TOKEN=true 的本地调试模式下才会把令牌直接返回。
    """
    require_realm("自助重置口令")
    user = service.find_user_by_email(db, body.email)
    token = None
    if user is not None and user.is_active:
        raw = service.create_reset_token(db, user)
        if service.get_settings().auth_dev_reveal_reset_token:
            token = raw
    payload = {
        "detail": "本演示未配置邮件发送，请联系空间管理员重置密码；如已收到重置令牌，可继续填写。"
    }
    if token:
        payload["dev_reset_token"] = token
    return payload


@router.post("/auth/password/reset")
def reset_password_with_token(body: ResetConfirm, db: DB):
    require_realm("自助重置口令")
    user = service.consume_reset_token(db, body.token, body.new_password)
    return {"email": user.email, "ok": True}


@router.post("/auth/2fa/setup", response_model=TotpSetupOut)
def totp_setup(db: DB, principal: CurrentPrincipal):
    """生成 TOTP 密钥与 otpauth 链接；此时尚未启用，需要一次验证码确认。"""
    user = require_local_user(db, principal)
    secret = service.start_totp(db, user)
    return TotpSetupOut(
        secret=secret,
        otpauth_uri=totp_uri(secret, user.email, service.get_settings().totp_issuer_name),
    )


@router.post("/auth/2fa/enable")
def totp_enable(body: TotpCode, db: DB, principal: CurrentPrincipal):
    user = require_local_user(db, principal)
    service.enable_totp(db, user, body.code)
    return {"totp_enabled": True}


@router.post("/auth/2fa/disable")
def totp_disable(body: TotpCode, db: DB, principal: CurrentPrincipal):
    user = require_local_user(db, principal)
    service.disable_totp(db, user, body.code)
    return {"totp_enabled": False}


def require_local_user(db, principal):
    if principal.id is None:
        raise HTTPException(404, "本地免鉴权模式下没有本地账号")
    user = db.get(User, principal.id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    return user


@router.post("/admin/users/{user_id}/password")
def reset_password(user_id: int, body: PasswordReset, db: DB, principal: AdminPrincipal):
    """Administrator sets a new local password (the old one is not required)."""
    user = get_user(db, user_id)
    if not principal.is_platform_admin and user.tenant_id != principal.tenant_id:
        raise HTTPException(404, "用户不存在")
    service.set_password(db, user, body.password, actor=principal)
    return {"user_id": user.id, "ok": True}


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=5, max_length=255)
    display_name: str = Field(min_length=2, max_length=60)
    password: str = Field(min_length=8, max_length=256)
    confirm_password: str = Field(min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("请输入有效邮箱")
        return value

    @field_validator("display_name")
    @classmethod
    def valid_name(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError("显示名至少两个字符")
        return value


@router.get("/auth/options")
def options():
    return {
        "registration_enabled": service.auth_mode() == service.ENFORCED
        and service.get_settings().public_registration_enabled
    }


@router.post("/auth/register", status_code=201)
def register(body: RegisterIn, db: DB, request: Request):
    from app.modules.auth import accounts

    require_realm("注册")
    if body.password != body.confirm_password:
        raise HTTPException(422, "两次密码不一致")
    user = accounts.register(
        db,
        body.email,
        body.password,
        body.display_name,
        request.client.host if request.client else "",
    )
    return {
        "email": user.email,
        "detail": "注册成功，已创建独立演示空间，请登录。邮箱未验证，仅供演示使用。",
    }
