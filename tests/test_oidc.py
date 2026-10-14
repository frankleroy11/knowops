"""P3b: OIDC login flow verified against a fully local fake identity provider."""

import base64
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.deps import get_db
from app.db.session import Base
from app.main import app
from app.modules.audit.models import AuditLog
from app.modules.auth import service as auth_service
from app.modules.auth.models import User
from app.modules.oidc import service as oidc_service
from app.modules.oidc import tokens as oidc_tokens
from app.modules.oidc.models import OidcLoginState
from app.modules.tenant.models import Tenant

ISSUER = "https://idp.test"
CLIENT_ID = "knowops-test"
REDIRECT_URI = "http://app.test/api/v1/auth/oidc/callback"
SETTINGS = Settings(
    oidc_enabled=True,
    oidc_issuer=ISSUER,
    oidc_client_id=CLIENT_ID,
    oidc_client_secret="client-secret",
    oidc_redirect_uri=REDIRECT_URI,
    oidc_default_role="viewer",
    oidc_default_tenant_slug="default",
)


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


@pytest.fixture(scope="module")
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def other_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def jwks_for(key, kid="primary"):
    numbers = key.public_key().public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": kid,
                "use": "sig",
                "alg": "RS256",
                "n": b64url(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
                "e": b64url(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")),
            }
        ]
    }


def make_id_token(
    key,
    subject="user-1",
    email="sso@corp",
    email_verified=True,
    audience=CLIENT_ID,
    issuer=ISSUER,
    nonce=None,
    expires_in=300,
    kid="primary",
):
    header = {"alg": "RS256", "typ": "JWT", "kid": kid}
    now = datetime.now(UTC)
    payload = {
        "iss": issuer,
        "aud": audience,
        "sub": subject,
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        "iat": int(now.timestamp()),
        "email": email,
        "email_verified": email_verified,
        "name": "SSO 用户",
    }
    if nonce is not None:
        payload["nonce"] = nonce
    signing_input = f"{b64url(json.dumps(header).encode())}.{b64url(json.dumps(payload).encode())}"
    signature = key.sign(signing_input.encode("ascii"), padding.PKCS1v15(), hashes.SHA256())
    return f"{signing_input}.{b64url(signature)}"


def make_provider(signing_key, other_key, state_nonce: dict):
    """Fake IdP: discovery, JWKS and token endpoint over httpx.MockTransport."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/.well-known/openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": f"{ISSUER}/authorize",
                    "token_endpoint": f"{ISSUER}/token",
                    "jwks_uri": f"{ISSUER}/jwks",
                },
            )
        if url.endswith("/jwks"):
            return httpx.Response(200, json=jwks_for(signing_key))
        if url.endswith("/token"):
            form = parse_qs(request.content.decode())
            if form.get("code") != ["good-code"]:
                return httpx.Response(400, json={"error": "invalid_grant"})
            assert form.get("client_id") == [CLIENT_ID]
            assert request.headers.get("authorization", "").startswith("Basic ")
            nonce = state_nonce.get("nonce")
            key = other_key if state_nonce.get("bad_signature") else signing_key
            token = make_id_token(
                key,
                nonce=None if state_nonce.get("bad_nonce") else nonce,
                audience=state_nonce.get("audience", CLIENT_ID),
                email_verified=state_nonce.get("email_verified", True),
                email=state_nonce.get("email", "sso@corp"),
                subject=state_nonce.get("subject", "user-1"),
                expires_in=state_nonce.get("expires_in", 300),
            )
            return httpx.Response(200, json={"id_token": token, "token_type": "Bearer"})
        return httpx.Response(404)

    return handler


@pytest.fixture
def enforced():
    """Tokens are only honoured when authentication is enforced."""
    with patch.object(auth_service, "get_settings", return_value=Settings(auth_mode="enforced")):
        yield


@pytest.fixture
def db_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'oidc.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory.begin() as db:
        db.add(Tenant(id=1, name="默认租户", slug="default"))
    return factory


@pytest.fixture
def client(db_factory):
    def database():
        with db_factory() as db:
            yield db

    app.dependency_overrides[get_db] = database
    try:
        # Redirects must not be followed: the browser, not this test, talks to the IdP.
        yield TestClient(app, follow_redirects=False)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def provider(signing_key, other_key):
    state = {"nonce": None, "bad_signature": False, "bad_nonce": False}
    handler = make_provider(signing_key, other_key, state)
    original = httpx.Client
    with (
        patch.object(oidc_service, "get_settings", return_value=SETTINGS),
        patch("app.modules.oidc.client.get_settings", return_value=SETTINGS),
        patch(
            "app.modules.oidc.client.httpx.Client",
            side_effect=lambda **kw: original(transport=httpx.MockTransport(handler), **kw),
        ),
    ):
        state["handler"] = handler
        yield state


def begin_login(client, web=False):
    response = client.get(f"/api/v1/auth/oidc/start?web={str(web).lower()}")
    assert response.status_code == 302, response.text
    query = parse_qs(urlparse(response.headers["location"]).query)
    return query["state"][0], query["nonce"][0]


def test_disabled_oidc_is_not_found(client, db_factory):
    with patch.object(oidc_service, "get_settings", return_value=Settings(oidc_enabled=False)):
        response = client.get("/api/v1/auth/oidc/start")
    assert response.status_code == 404
    assert response.json()["detail"] == "未启用 OIDC 单点登录"


def test_start_redirects_with_state_nonce_and_pkce_free_params(client, provider):
    response = client.get("/api/v1/auth/oidc/start")
    location = urlparse(response.headers["location"])
    query = parse_qs(location.query)
    assert location.geturl().startswith(f"{ISSUER}/authorize?")
    assert query["client_id"] == [CLIENT_ID]
    assert query["redirect_uri"] == [REDIRECT_URI]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["openid email profile"]
    assert query["state"][0] and query["nonce"][0]


def test_login_state_is_stamped_with_the_api_clock(client, provider, db_factory):
    """Regression: the DB clock may be UTC while the API clock is local, which
    previously made every freshly created login state look expired."""
    state, _ = begin_login(client)
    with db_factory() as db:
        row = db.get(OidcLoginState, state)
    assert row is not None
    assert abs((datetime.now() - row.created_at).total_seconds()) < 60


def test_full_login_issues_working_token_and_provisions_user(client, provider, db_factory, enforced):
    state, nonce = begin_login(client)
    provider["nonce"] = nonce
    response = client.get(f"/api/v1/auth/oidc/callback?code=good-code&state={state}")
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    assert token.startswith("knp_")
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["email"] == "sso@corp" and me["role"] == "viewer" and me["tenant_id"] == 1
    with db_factory() as db:
        user = db.scalar(select(User).where(User.email == "sso@corp"))
        assert (user.oidc_issuer, user.oidc_subject) == (ISSUER, "user-1")
        actions = [row.action for row in db.scalars(select(AuditLog))]
    assert "user.oidc.provision" in actions and "auth.oidc.login" in actions


def test_second_login_reuses_the_same_account(client, provider, db_factory):
    state, nonce = begin_login(client)
    provider["nonce"] = nonce
    first = client.get(f"/api/v1/auth/oidc/callback?code=good-code&state={state}").json()
    state, nonce = begin_login(client)
    provider["nonce"] = nonce
    second = client.get(f"/api/v1/auth/oidc/callback?code=good-code&state={state}").json()
    assert first["user"]["id"] == second["user"]["id"]
    with db_factory() as db:
        assert len(list(db.scalars(select(User)))) == 1


def test_existing_local_account_is_linked_without_losing_its_role(client, provider, db_factory):
    with db_factory.begin() as db:
        db.add(User(id=7, email="sso@corp", display_name="既有管理员", role="admin", tenant_id=1))
    state, nonce = begin_login(client)
    provider["nonce"] = nonce
    body = client.get(f"/api/v1/auth/oidc/callback?code=good-code&state={state}").json()
    assert body["user"]["id"] == 7 and body["user"]["role"] == "admin"
    with db_factory() as db:
        user = db.get(User, 7)
        assert (user.oidc_issuer, user.oidc_subject) == (ISSUER, "user-1")
        assert "user.oidc.link" in [row.action for row in db.scalars(select(AuditLog))]


def test_email_bound_to_another_subject_is_rejected(client, provider, db_factory):
    with db_factory.begin() as db:
        db.add(
            User(
                id=8,
                email="sso@corp",
                role="viewer",
                tenant_id=1,
                oidc_issuer=ISSUER,
                oidc_subject="someone-else",
            )
        )
    state, nonce = begin_login(client)
    provider["nonce"] = nonce
    response = client.get(f"/api/v1/auth/oidc/callback?code=good-code&state={state}")
    assert response.status_code == 401


def test_unverified_email_cannot_provision(client, provider):
    state, nonce = begin_login(client)
    provider["nonce"] = nonce
    provider["email_verified"] = False
    assert client.get(f"/api/v1/auth/oidc/callback?code=good-code&state={state}").status_code == 401


def test_state_is_single_use(client, provider):
    state, nonce = begin_login(client)
    provider["nonce"] = nonce
    assert client.get(f"/api/v1/auth/oidc/callback?code=good-code&state={state}").status_code == 200
    assert client.get(f"/api/v1/auth/oidc/callback?code=good-code&state={state}").status_code == 400


def test_unknown_state_and_missing_code_are_rejected(client, provider):
    assert client.get("/api/v1/auth/oidc/callback?code=good-code&state=nope").status_code == 400
    state, nonce = begin_login(client)
    provider["nonce"] = nonce
    assert client.get(f"/api/v1/auth/oidc/callback?state={state}").status_code == 400
    assert client.get(f"/api/v1/auth/oidc/callback?code=good-code&state={state}&error=access_denied").status_code == 401


def test_rejected_assertions_never_issue_a_token(client, provider):
    for case in ("bad_signature", "bad_nonce"):
        state, nonce = begin_login(client)
        provider["nonce"] = nonce
        provider[case] = True
        try:
            assert client.get(f"/api/v1/auth/oidc/callback?code=good-code&state={state}").status_code == 401
        finally:
            provider[case] = False
    state, nonce = begin_login(client)
    provider["nonce"] = nonce
    provider["audience"] = "another-client"
    try:
        assert client.get(f"/api/v1/auth/oidc/callback?code=good-code&state={state}").status_code == 401
    finally:
        provider["audience"] = CLIENT_ID
    state, nonce = begin_login(client)
    provider["nonce"] = nonce
    provider["expires_in"] = -600
    try:
        assert client.get(f"/api/v1/auth/oidc/callback?code=good-code&state={state}").status_code == 401
    finally:
        provider["expires_in"] = 300


def test_rejected_code_exchange_is_401(client, provider):
    state, nonce = begin_login(client)
    provider["nonce"] = nonce
    assert client.get(f"/api/v1/auth/oidc/callback?code=wrong&state={state}").status_code == 401


def test_web_callback_stores_the_token_and_redirects(client, provider):
    state, nonce = begin_login(client, web=True)
    provider["nonce"] = nonce
    response = client.get(f"/api/v1/auth/oidc/callback?code=good-code&state={state}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert oidc_service.TOKEN_STORAGE_KEY in response.text
    assert "location.replace" in response.text and "knp_" in response.text


def test_token_module_rejects_unsigned_and_unknown_algorithms(signing_key):
    jwks = jwks_for(signing_key)
    unsigned = f"{b64url(json.dumps({'alg': 'none'}).encode())}.{b64url(b'{}')}."
    with pytest.raises(oidc_tokens.TokenError):
        oidc_tokens.verify_id_token(unsigned, jwks, ISSUER, CLIENT_ID)
    unknown = f"{b64url(json.dumps({'alg': 'HS256', 'kid': 'primary'}).encode())}.{b64url(b'{}')}.{b64url(b'x')}"
    with pytest.raises(oidc_tokens.TokenError):
        oidc_tokens.verify_id_token(unknown, jwks, ISSUER, CLIENT_ID)


def test_token_module_requires_nonce_and_audience(signing_key):
    token = make_id_token(signing_key, nonce="n1")
    with pytest.raises(oidc_tokens.TokenError):
        oidc_tokens.verify_id_token(token, jwks_for(signing_key), ISSUER, CLIENT_ID, nonce="other")
    assert (
        oidc_tokens.verify_id_token(token, jwks_for(signing_key), ISSUER, CLIENT_ID, nonce="n1").email
        == "sso@corp"
    )
