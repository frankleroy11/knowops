"""Embedding 适配器：契约见 base，真实本地实现见 local。"""

from app.adapters.embeddings.base import Embedder, EmbeddingError, l2_normalize
from app.adapters.embeddings.local import get_embedder

__all__ = ["Embedder", "EmbeddingError", "get_embedder", "l2_normalize"]
