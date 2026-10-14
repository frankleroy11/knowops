"""API token and password hashing.

Tokens are high-entropy random strings, never user-chosen passwords, so a plain
SHA-256 digest is enough to make a leaked database row unusable. Only the digest
is stored; the raw token is shown once at creation time.

Passwords use `hashlib.scrypt` (stdlib, memory-hard) with a per-password salt;
no extra dependency is needed, which matters on an offline machine.
"""

import base64
import hashlib
import hmac
import secrets

TOKEN_PREFIX = "knp_"
SCRYPT_N, SCRYPT_R, SCRYPT_P, SCRYPT_LEN = 2**14, 8, 1, 32


def generate_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def token_hint(raw: str) -> str:
    """Short, non-reversible label for logs and CLI output."""
    return raw[:8] + "…"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_LEN,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        algorithm, n, r, p, salt_b64, digest_b64 = stored.split("$")
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_b64)
        expected = base64.urlsafe_b64decode(digest_b64)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)

