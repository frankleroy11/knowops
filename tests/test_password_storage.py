"""演示明文模式与历史摘要的兼容性。"""

import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.modules.auth.security import hash_password, verify_password
from app.modules.auth.service import validate_password


def test_plaintext_storage_unicode_and_format_prefix(monkeypatch):
    monkeypatch.setattr(get_settings(), "password_storage", "plaintext")
    password = "中文$plaintext$demo123"
    stored = hash_password(password)
    assert stored == "plaintext$" + password
    assert verify_password(password, stored)
    assert not verify_password("wrong", stored)


def test_hashes_remain_readable_when_switching_storage(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "password_storage", "scrypt")
    hashed = hash_password("Demo12345")
    assert hashed.startswith("scrypt$")
    monkeypatch.setattr(settings, "password_storage", "plaintext")
    assert verify_password("Demo12345", hashed)
    plain = hash_password("Demo12345")
    monkeypatch.setattr(settings, "password_storage", "scrypt")
    assert verify_password("Demo12345", plain)
    assert not verify_password("wrong", hashed)
    assert not verify_password("Demo12345", None)


def test_plaintext_column_capacity(monkeypatch):
    monkeypatch.setattr(get_settings(), "password_storage", "plaintext")
    password = "Aa1" + "x" * 242
    assert len(hash_password(password)) == 255
    with pytest.raises(ValueError):
        hash_password(password + "x")
    with pytest.raises(HTTPException) as error:
        validate_password(password + "x")
    assert error.value.status_code == 422
