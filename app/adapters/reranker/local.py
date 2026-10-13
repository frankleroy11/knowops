"""Optional local cross-encoder; normalized scores are ranking scores, not probabilities."""

import math
from functools import lru_cache
from threading import RLock

from app.core.config import get_settings

_lock = RLock()


class LocalReranker:
    def __init__(self):
        import torch
        from sentence_transformers import CrossEncoder

        s = get_settings()
        self.model_name = s.reranker_model
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.model = CrossEncoder(
            s.reranker_model_path or self.model_name,
            device=self.device,
            max_length=s.reranker_max_length,
        )

    def score(self, query, hits):
        if not hits:
            return []
        with _lock:
            scores = self.model.predict(
                [(query, h["content"]) for h in hits],
                batch_size=get_settings().reranker_batch_size,
                show_progress_bar=False,
            )
        result = [float(s) for s in scores]
        if len(result) != len(hits) or not all(math.isfinite(s) for s in result):
            raise ValueError("Invalid reranker output")
        return result


@lru_cache
def _cached_reranker():
    return LocalReranker()


def get_reranker():
    with _lock:
        return _cached_reranker()


def select_ranked(hits, scores, top_k, max_per_document=0):
    ranked = sorted(
        [{**h, "rerank_score": float(s)} for h, s in zip(hits, scores, strict=True)],
        key=lambda h: h["rerank_score"],
        reverse=True,
    )
    if not max_per_document:
        return ranked[:top_k]
    selected, skipped, counts = [], [], {}
    for hit in ranked:
        doc = hit["document_id"]
        if counts.get(doc, 0) >= max_per_document:
            skipped.append(hit)
        else:
            selected.append(hit)
            counts[doc] = counts.get(doc, 0) + 1
        if len(selected) == top_k:
            return selected
    # Soft diversity cap: fill remaining slots if too few distinct documents.
    return selected + skipped[: top_k - len(selected)]


def rerank_hits(query, hits, top_k, max_per_document=0):
    if not hits:
        return []
    return select_ranked(hits, get_reranker().score(query, hits), top_k, max_per_document)
