"""OIDC authorization-code login endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from app.db.deps import DB
from app.modules.audit import service as audit
from app.modules.auth import service as auth_service
from app.modules.oidc import service
from app.modules.oidc.client import OidcClient

router = APIRouter(tags=["单点登录"])


class OidcStatus(BaseModel):
    enabled: bool


@router.get("/auth/oidc/status", response_model=OidcStatus)
def status():
    """Unauthenticated on purpose: the login screen needs it before any token."""
    return OidcStatus(enabled=service.enabled())


@router.get("/auth/oidc/start")
def start(db: DB, web: bool = True):
    """Begin the authorization-code flow; state and nonce are stored server-side."""
    service.require_enabled()
    service.prune_login_states(db)  # 顺手清理过期/已消费的登录状态
    login_state = service.create_login_state(db, web)
    metadata = OidcClient().discovery()
    return RedirectResponse(
        service.authorization_url(metadata, login_state.state, login_state.nonce),
        status_code=302,
    )


@router.get("/auth/oidc/logout")
def logout(web: bool = True):
    """RP-initiated single logout: send the browser to the provider's end-session URL.

    The local API token is revoked separately by `POST /auth/logout`, which the SPA
    calls first; this endpoint only ends the provider-side session.
    """
    service.require_enabled()
    metadata = OidcClient().discovery()
    target = service.logout_url(metadata)
    if target is None:
        raise HTTPException(404, "OIDC 提供方未声明 end_session_endpoint")
    if web:
        return RedirectResponse(target, status_code=302)
    return {"logout_url": target}


@router.get("/auth/oidc/callback")
def callback(db: DB, code: str = "", state: str = "", error: str = ""):
    service.require_enabled()
    if error:
        raise HTTPException(401, f"OIDC 返回错误：{error}")
    if not code:
        raise HTTPException(400, "缺少授权码")
    login_state = service.consume_login_state(db, state)
    user, id_token = service.authenticate(db, code, login_state)
    raw = auth_service.issue_token(db, user, "oidc", id_token=id_token)
    audit.record(db, user, "auth.oidc.login", "user", user.id, f"email={user.email}")
    if login_state.web:
        return HTMLResponse(service.web_callback_html(raw))
    return {
        "token": raw,
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
            "tenant_id": user.tenant_id,
        },
    }
