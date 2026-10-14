"""Offline switch keeps cached models from triggering hub requests."""

import os

from app.adapters.embeddings.local import apply_offline_env
from app.core.config import Settings


def test_offline_flag_controls_hf_env(monkeypatch):
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)

    apply_offline_env(Settings(embedding_offline=False))
    assert "HF_HUB_OFFLINE" not in os.environ

    apply_offline_env(Settings(embedding_offline=True))
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "1"


def test_offline_flag_does_not_override_an_explicit_value(monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    apply_offline_env(Settings(embedding_offline=True))
    assert os.environ["HF_HUB_OFFLINE"] == "0"
