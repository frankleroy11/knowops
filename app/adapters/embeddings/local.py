"""Lazy local BGE-M3 loading; no network/model work during API startup."""

import os
from functools import lru_cache

from app.core.config import get_settings


def apply_offline_env(settings) -> None:
    """Pin Hugging Face to the local cache when the model is already downloaded.

    Otherwise sentence-transformers issues a hub HEAD request on every model load,
    which on an offline machine stalls for minutes - and the caller may be holding a
    database lock meanwhile. Opt in with EMBEDDING_OFFLINE=1.
    """
    if not settings.embedding_offline:
        return
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


class LocalEmbedder:
    normalized = True

    def __init__(self):
        s = get_settings()
        apply_offline_env(s)
        import torch
        from sentence_transformers import SentenceTransformer

        if s.embedder_provider != "bge_m3":
            raise ValueError("Only real BGE-M3 embeddings are supported")
        self.model_name = s.embedding_model
        self.dim = s.embedding_dim
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.model = SentenceTransformer(
            s.embedding_model_path or s.embedding_model, device=self.device
        )
        self.model.max_seq_length = s.embedding_max_length
        if self.model.get_sentence_embedding_dimension() != self.dim:
            raise ValueError("Embedding dimension mismatch")

    def encode(self, texts, *, is_query=False):
        return self.model.encode(
            list(texts),
            batch_size=get_settings().embedding_batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()


@lru_cache
def get_embedder():
    return LocalEmbedder()
