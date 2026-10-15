# 中文导读：
# 安全基础工具：令牌摘要、密码散列和 TOTP 校验
# 数据库保存验证所需的摘要信息，原始访问令牌只应在签发时交付

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
import struct
import time

TOKEN_PREFIX = "knp_"
SCRYPT_N, SCRYPT_R, SCRYPT_P, SCRYPT_LEN = 2**14, 8, 1, 32


def generate_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


# 访问令牌以摘要形式入库，泄露数据库摘要不应直接得到可用的原始令牌。
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


# 使用保存的散列参数验证密码，不把明文密码与数据库字段直接比较。
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



# --- 二次验证（TOTP，RFC 6238）---

TOTP_STEP = 30
TOTP_DIGITS = 6


def generate_totp_secret() -> str:
    """base32 随机密钥（16 字节，去掉填充，便于输入 Authenticator）。"""
    return base64.b32encode(secrets.token_bytes(16)).decode("ascii").rstrip("=")


def totp_code(secret: str, at: int | None = None) -> str:
    """按 TOTP 算法算出某时刻的 6 位验证码。"""
    counter = int((at if at is not None else time.time()) // TOTP_STEP)
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10**TOTP_DIGITS)).zfill(TOTP_DIGITS)


# 按允许的时间窗口核验动态验证码，处理客户端与服务端的小幅时钟偏差。
def verify_totp(secret: str | None, code: str, window: int = 1, at: int | None = None) -> bool:
    """允许前后 window 个时间步，避免客户端时钟轻微偏差导致登录失败。"""
    if not secret or not code:
        return False
    candidate = str(code).strip().replace(" ", "")
    if not candidate.isdigit():
        return False
    moment = at if at is not None else int(time.time())
    return any(
        hmac.compare_digest(totp_code(secret, moment + step * TOTP_STEP), candidate)
        for step in range(-window, window + 1)
    )


def totp_uri(secret: str, account: str, issuer: str) -> str:
    """otpauth:// 链接，供 Authenticator 扫码/手动录入。"""
    from urllib.parse import quote

    label = quote(f"{issuer}:{account}", safe="")
    return (
        f"otpauth://totp/{label}?secret={secret}"
        f"&issuer={quote(issuer, safe='')}&algorithm=SHA1&digits={TOTP_DIGITS}&period={TOTP_STEP}"
    )
