"""Lazy local BGE-M3 loading; no network/model work during API startup."""

from functools import lru_cache

from app.core.config import get_settings


class LocalEmbedder:
    normalized = True

    def __init__(self):
        import torch
        from sentence_transformers import SentenceTransformer

        s = get_settings()
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
