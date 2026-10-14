"""Minimal OIDC ID-token verification on top of `cryptography`.

PyJWT/python-jose are not installed and packages cannot be added offline, so the
RS256 family signature check and the claim checks are implemented here directly.
Only RSA signatures are accepted: `none` and HMAC algorithms are rejected, which
prevents the classic algorithm-confusion attacks.
"""

import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

ALGORITHMS = {
    "RS256": hashes.SHA256,
    "RS384": hashes.SHA384,
    "RS512": hashes.SHA512,
}


class TokenError(ValueError):
    """Raised for any ID token that must not be trusted."""


class UnknownKeyError(TokenError):
    """The token names a `kid` we do not have yet: the caller may refresh JWKS."""


@dataclass(frozen=True)
class IdTokenClaims:
    subject: str
    email: str
    email_verified: bool
    name: str
    raw: dict


def _b64url_decode(segment: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
    except Exception as exc:
        raise TokenError("ID token 编码无效") from exc


def _json_segment(segment: str) -> dict:
    try:
        decoded = json.loads(_b64url_decode(segment))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise TokenError("ID token 结构无效") from exc
    if not isinstance(decoded, dict):
        raise TokenError("ID token 结构无效")
    return decoded


def public_key_from_jwk(jwk: dict):
    if jwk.get("kty") != "RSA":
        raise TokenError("不支持的密钥类型")
    try:
        modulus = int.from_bytes(_b64url_decode(jwk["n"]), "big")
        exponent = int.from_bytes(_b64url_decode(jwk["e"]), "big")
    except KeyError as exc:
        raise TokenError("密钥缺少参数") from exc
    return rsa.RSAPublicNumbers(exponent, modulus).public_key()


def select_jwk(jwks: dict, kid: str | None) -> dict:
    keys = jwks.get("keys") or []
    if kid:
        for key in keys:
            if key.get("kid") == kid:
                return key
        raise UnknownKeyError("找不到匹配的签名密钥")
    if len(keys) == 1:
        return keys[0]
    raise UnknownKeyError("无法确定签名密钥")


def verify_id_token(
    token: str,
    jwks: dict,
    issuer: str,
    audience: str,
    nonce: str | None = None,
    clock_skew: int = 60,
    now: datetime | None = None,
) -> IdTokenClaims:
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenError("ID token 格式无效")
    header = _json_segment(parts[0])
    algorithm = header.get("alg")
    if algorithm not in ALGORITHMS:
        raise TokenError("不支持的签名算法")
    payload = _json_segment(parts[1])
    signature = _b64url_decode(parts[2])
    key = public_key_from_jwk(select_jwk(jwks, header.get("kid")))
    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    try:
        key.verify(signature, signing_input, padding.PKCS1v15(), ALGORITHMS[algorithm]())
    except InvalidSignature as exc:
        raise TokenError("ID token 签名校验失败") from exc

    timestamp = (now or datetime.now(UTC)).timestamp()
    if payload.get("iss") != issuer:
        raise TokenError("签发方不符")
    audiences = payload.get("aud")
    if isinstance(audiences, str):
        audiences = [audiences]
    if not isinstance(audiences, list) or audience not in audiences:
        raise TokenError("受众不符")
    try:
        expires = float(payload["exp"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TokenError("ID token 缺少有效期") from exc
    if expires < timestamp - clock_skew:
        raise TokenError("ID token 已过期")
    if "nbf" in payload and float(payload["nbf"]) > timestamp + clock_skew:
        raise TokenError("ID token 尚未生效")
    if nonce is not None and payload.get("nonce") != nonce:
        raise TokenError("nonce 不匹配")
    subject = payload.get("sub")
    if not subject:
        raise TokenError("ID token 缺少 sub")
    return IdTokenClaims(
        subject=str(subject),
        email=str(payload.get("email") or "").strip().lower(),
        email_verified=bool(payload.get("email_verified")),
        name=str(payload.get("name") or payload.get("preferred_username") or "").strip(),
        raw=payload,
    )
