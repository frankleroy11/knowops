"""API token generation and hashing.

Tokens are high-entropy random strings, never user-chosen passwords, so a plain
SHA-256 digest is enough to make a leaked database row unusable. Only the digest
is stored; the raw token is shown once at creation time.
"""

import hashlib
import secrets

TOKEN_PREFIX = "knp_"


def generate_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def token_hint(raw: str) -> str:
    """Short, non-reversible label for logs and CLI output."""
    return raw[:8] + "…"
