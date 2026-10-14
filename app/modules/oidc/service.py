"""OIDC login state, account linking/auto-provisioning and local token issuance."""

import json
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlsplit

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.audit import service as audit
from app.modules.auth import service as auth_service
from app.modules.auth.models import User
from app.modules.oidc.client import OidcClient
from app.modules.oidc.models import OidcLoginState
from app.modules.oidc.tokens import TokenError, UnknownKeyError, verify_id_token
from app.modules.tenant import service as tenants

STATE_TTL = timedelta(minutes=10)
TOKEN_STORAGE_KEY = "knowops.token"
METHOD_STORAGE_KEY = "knowops.login_method"


def enabled() -> bool:
    settings = get_settings()
    return bool(settings.oidc_enabled and settings.oidc_issuer and settings.oidc_client_id)


def require_enabled() -> None:
    if not enabled():
        raise HTTPException(404, "未启用 OIDC 单点登录")


def create_login_state(db: Session, web: bool) -> OidcLoginState:
    # Stamp the row with the API clock: expiry is compared against the same clock,
    # while the DB's NOW() may sit in another time zone (MySQL in Docker is UTC).
    row = OidcLoginState(
        state=secrets.token_urlsafe(24),
        nonce=secrets.token_urlsafe(24),
        web=web,
        created_at=datetime.now(),
    )
    db.add(row)
    db.commit()
    return row


def consume_login_state(db: Session, state: str) -> OidcLoginState:
    """Single use: a replayed or unknown state must never start a session."""
    row = db.get(OidcLoginState, state) if state else None
    if row is None or row.consumed_at is not None:
        raise HTTPException(400, "登录状态无效或已使用")
    if row.created_at is not None and datetime.now() - row.created_at > STATE_TTL:
        raise HTTPException(400, "登录状态已过期")
    row.consumed_at = datetime.now()
    db.commit()
    return row


def authorization_url(metadata: dict, state: str, nonce: str) -> str:
    settings = get_settings()
    query = urlencode(
        {
            "response_type": "code",
            "client_id": settings.oidc_client_id,
            "redirect_uri": settings.oidc_redirect_uri,
            "scope": settings.oidc_scopes,
            "state": state,
            "nonce": nonce,
        }
    )
    endpoint = metadata["authorization_endpoint"]
    return endpoint + ("&" if "?" in endpoint else "?") + query


def authenticate(db: Session, code: str, login_state: OidcLoginState) -> User:
    settings = get_settings()
    client = OidcClient(settings)
    metadata = client.discovery()
    tokens = client.exchange_code(metadata["token_endpoint"], code, settings.oidc_redirect_uri)

    def verify(keys):
        return verify_id_token(
            tokens["id_token"],
            keys,
            issuer=metadata.get("issuer") or settings.oidc_issuer,
            audience=settings.oidc_client_id,
            nonce=login_state.nonce,
            clock_skew=settings.oidc_clock_skew,
        )

    jwks_uri = metadata["jwks_uri"]
    try:
        claims = verify(client.jwks(jwks_uri))
    except UnknownKeyError:
        # Provider rotated its signing key: refresh once, then give up.
        try:
            claims = verify(client.jwks(jwks_uri, refresh=True))
        except TokenError as exc:
            raise HTTPException(401, f"ID token 校验失败：{exc}") from None
    except TokenError as exc:
        raise HTTPException(401, f"ID token 校验失败：{exc}") from None
    return map_user(db, claims)


def mapped_role(settings, claims) -> str | None:
    """Translate an IdP group claim into a local role, if configured."""
    if not settings.oidc_role_map:
        return None
    try:
        mapping = json.loads(settings.oidc_role_map)
    except ValueError:
        return None
    if not isinstance(mapping, dict):
        return None
    raw = claims.raw.get(settings.oidc_role_claim)
    groups = [raw] if isinstance(raw, str) else list(raw or [])
    for group, role in mapping.items():
        if group in groups and role in ("admin", "editor", "viewer"):
            return role
    return None


def sync_role(db: Session, user: User, settings, claims) -> None:
    """Only touch an existing account's role when role sync is enabled."""
    if not settings.oidc_role_sync:
        return
    mapped = mapped_role(settings, claims)
    if mapped is None or mapped == user.role:
        return
    user.role = mapped
    db.commit()
    audit.record(db, user, "user.oidc.role", "user", user.id, f"role={mapped}")


def map_user(db: Session, claims) -> User:
    """Link an existing account or provision one, never silently merging identities."""
    settings = get_settings()
    linked = db.scalar(
        select(User).where(
            User.oidc_issuer == settings.oidc_issuer,
            User.oidc_subject == claims.subject,
        )
    )
    if linked is not None:
        if not linked.is_active:
            raise HTTPException(401, "账号已停用，请联系管理员")
        sync_role(db, linked, settings, claims)
        return linked

    if not claims.email or not claims.email_verified:
        raise HTTPException(401, "OIDC 未提供已验证邮箱，无法开通账号")

    existing = db.scalar(select(User).where(User.email == claims.email))
    if existing is not None:
        if existing.oidc_subject and existing.oidc_subject != claims.subject:
            raise HTTPException(401, "该邮箱已绑定其他 OIDC 身份")
        if not existing.is_active:
            raise HTTPException(401, "账号已停用，请联系管理员")
        existing.oidc_issuer = settings.oidc_issuer
        existing.oidc_subject = claims.subject
        db.commit()
        audit.record(db, existing, "user.oidc.link", "user", existing.id, f"email={existing.email}")
        sync_role(db, existing, settings, claims)
        return existing

    try:
        tenant = tenants.get_tenant_by_slug(db, settings.oidc_default_tenant_slug)
        user = auth_service.create_user(
            db,
            claims.email,
            mapped_role(settings, claims) or settings.oidc_default_role,
            claims.name,
            tenant.id if tenant else None,
        )
    except HTTPException as exc:
        raise HTTPException(503, f"OIDC 账号开通配置有误：{exc.detail}") from None
    user.oidc_issuer = settings.oidc_issuer
    user.oidc_subject = claims.subject
    db.commit()
    audit.record(
        db,
        user,
        "user.oidc.provision",
        "user",
        user.id,
        f"email={user.email} role={user.role} tenant={user.tenant_id}",
    )
    return user


def absolute_web_url(path: str) -> str:
    """Providers require an absolute `post_logout_redirect_uri`; derive our origin
    from the registered callback URL when only a path is configured."""
    if not path or path.startswith(("http://", "https://")):
        return path
    callback = get_settings().oidc_redirect_uri
    if not callback.startswith(("http://", "https://")):
        return path
    parts = urlsplit(callback)
    return f"{parts.scheme}://{parts.netloc}{path}"


def logout_url(metadata: dict) -> str | None:
    """RP-initiated logout target, or None when the provider does not support it."""
    endpoint = metadata.get("end_session_endpoint")
    if not endpoint:
        return None
    settings = get_settings()
    target = settings.oidc_post_logout_redirect or settings.oidc_web_redirect
    query = urlencode(
        {
            "client_id": settings.oidc_client_id,
            "post_logout_redirect_uri": absolute_web_url(target),
        }
    )
    return endpoint + ("&" if "?" in endpoint else "?") + query


def web_callback_html(token: str) -> str:
    """Hand the freshly issued token to the SPA without putting it in the URL."""
    settings = get_settings()
    target = settings.oidc_web_redirect or "/ui/"
    script = (
        "localStorage.setItem(TOKEN_KEY, TOKEN);\n"
        "localStorage.setItem(METHOD_KEY, \"oidc\");\n"
        "location.replace(TARGET);"
        .replace("TOKEN_KEY", json.dumps(TOKEN_STORAGE_KEY))
        .replace("METHOD_KEY", json.dumps(METHOD_STORAGE_KEY))
        .replace("TOKEN", json.dumps(token))
        .replace("TARGET", json.dumps(target))
    )
    return (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        "<title>KnowOps 登录中…</title></head><body>"
        "<p>登录成功，正在跳转…</p><script>" + script + "</script></body></html>"
    )
