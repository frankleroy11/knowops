"""Offline tests must not inherit the developer's live authentication mode."""

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def isolated_auth_default(monkeypatch):
    # Security tests explicitly override this to enforced in their own fixtures.
    monkeypatch.setattr(get_settings(), 'auth_mode', 'off')

    # 旧有路由单测不连接真实 FAQ / Redis；该功能由专门测试显式开启。
    monkeypatch.setattr(get_settings(), "faq_enabled", False)
    monkeypatch.setattr(get_settings(), "answer_cache_enabled", False)
