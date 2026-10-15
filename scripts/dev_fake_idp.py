"""Local fake OIDC provider for end-to-end development checks (never for production).

Run it next to the API to exercise the real HTTP authorization-code flow:

    python scripts/dev_fake_idp.py --port 8020 --redirect-uri http://127.0.0.1:8011/api/v1/auth/oidc/callback

Then start the API with OIDC_ISSUER=http://127.0.0.1:8020 etc. The provider is
deliberately permissive: any `/authorize` request immediately redirects back with
the fixed code below, and `/token` returns an ID token signed by a key generated
at startup (exposed through `/jwks`).
"""

import argparse
import base64
import json
from datetime import UTC, datetime, timedelta

import uvicorn
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

CODE = "good-code"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
# Set by the CLI flags below; a rotation changes both the key and its `kid`.
KID = "dev"
GROUPS: list[str] = []
ISSUER = "http://127.0.0.1:8020"
PENDING: dict[str, dict] = {}

app = FastAPI(title="KnowOps fake OIDC provider")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def id_token(nonce: str, client_id: str, email: str) -> str:
    header = {"alg": "RS256", "typ": "JWT", "kid": KID}
    now = datetime.now(UTC)
    payload = {
        "iss": ISSUER,
        "aud": client_id,
        "sub": "dev-user-1",
        "exp": int((now + timedelta(minutes=10)).timestamp()),
        "iat": int(now.timestamp()),
        "nonce": nonce,
        "email": email,
        "email_verified": True,
        "name": "SSO 联调用户",
        "groups": GROUPS,
    }
    signing_input = f"{b64url(json.dumps(header).encode())}.{b64url(json.dumps(payload).encode())}"
    signature = KEY.sign(signing_input.encode("ascii"), padding.PKCS1v15(), hashes.SHA256())
    return f"{signing_input}.{b64url(signature)}"


@app.get("/.well-known/openid-configuration")
def discovery():
    return {
        "issuer": ISSUER,
        "authorization_endpoint": f"{ISSUER}/authorize",
        "token_endpoint": f"{ISSUER}/token",
        "jwks_uri": f"{ISSUER}/jwks",
        "end_session_endpoint": f"{ISSUER}/logout",
    }


@app.get("/jwks")
def jwks():
    numbers = KEY.public_key().public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": KID,
                "use": "sig",
                "alg": "RS256",
                "n": b64url(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
                "e": b64url(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")),
            }
        ]
    }


@app.get("/logout")
def logout(request: Request):
    """Provider-side end session: immediately bounce back to the RP."""
    target = request.query_params.get("post_logout_redirect_uri") or "/"
    return RedirectResponse(target, status_code=302)


@app.get("/authorize")
def authorize(request: Request):
    params = request.query_params
    PENDING[CODE] = {
        "nonce": params.get("nonce", ""),
        "client_id": params.get("client_id", ""),
        "redirect_uri": params.get("redirect_uri", ""),
    }
    target = f"{params.get('redirect_uri', '')}?code={CODE}&state={params.get('state', '')}"
    return RedirectResponse(target, status_code=302)


@app.post("/token")
def token(grant_type: str = Form(""), code: str = Form(""), client_id: str = Form("")):
    if grant_type != "authorization_code" or code not in PENDING:
        return JSONResponse({"error": "invalid_grant"}, status_code=400)
    context = PENDING.pop(code)
    return {
        "access_token": "dev-access-token",
        "token_type": "Bearer",
        "id_token": id_token(context["nonce"], context["client_id"] or client_id, "sso@dev.local"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8020)
    parser.add_argument("--groups", default="", help="逗号分隔的组声明，写入 id_token 的 groups")
    parser.add_argument(
        "--rotate",
        action="store_true",
        help="换用新密钥与 kid=rotated，用于验证验证方的 JWKS 刷新",
    )
    arguments = parser.parse_args()
    GROUPS.extend([g for g in arguments.groups.split(",") if g])
    if arguments.rotate:
        KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        KID = "rotated"
    uvicorn.run(app, host="127.0.0.1", port=arguments.port, log_level="warning")
