"""OIDC discovery, JWKS fetch and authorization-code exchange."""

import httpx
from fastapi import HTTPException

from app.core.config import get_settings


class OidcClient:
    def __init__(self, settings=None, timeout: float = 10.0):
        self.settings = settings or get_settings()
        self.timeout = timeout

    def _get_json(self, url: str) -> dict:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
        except httpx.HTTPError as exc:
            raise HTTPException(503, "OIDC 提供方不可达") from exc
        if response.status_code != 200:
            raise HTTPException(503, "OIDC 提供方返回异常")
        try:
            return response.json()
        except ValueError as exc:
            raise HTTPException(503, "OIDC 响应不是 JSON") from exc

    def discovery(self) -> dict:
        issuer = self.settings.oidc_issuer.rstrip("/")
        metadata = self._get_json(issuer + "/.well-known/openid-configuration")
        for field in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
            if not metadata.get(field):
                raise HTTPException(503, "OIDC 元数据不完整")
        return metadata

    def jwks(self, jwks_uri: str) -> dict:
        return self._get_json(jwks_uri)

    def exchange_code(self, token_endpoint: str, code: str, redirect_uri: str) -> dict:
        settings = self.settings
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": settings.oidc_client_id,
        }
        auth = None
        if settings.oidc_client_secret:
            auth = (settings.oidc_client_id, settings.oidc_client_secret)
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(token_endpoint, data=payload, auth=auth)
        except httpx.HTTPError as exc:
            raise HTTPException(503, "OIDC 令牌端点不可达") from exc
        if response.status_code != 200:
            raise HTTPException(401, "OIDC 授权码交换失败")
        try:
            body = response.json()
        except ValueError as exc:
            raise HTTPException(401, "OIDC 令牌响应无效") from exc
        if not body.get("id_token"):
            raise HTTPException(401, "OIDC 未返回 id_token")
        return body
