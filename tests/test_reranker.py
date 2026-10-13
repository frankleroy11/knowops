import pytest
from pydantic import ValidationError

from app.adapters.reranker.local import select_ranked
from app.modules.retrieval.router import Query

HITS = [
    {"chunk_id": i, "document_id": d, "score": 0.9, "content": "正文"}
    for i, d in enumerate([1, 1, 1, 2, 3])
]


def test_ranking_preserves_dense_score_and_input():
    r = select_ranked(HITS, [0.1, 0.2, 0.3, 0.9, 0.5], 3)
    assert [x["chunk_id"] for x in r] == [3, 4, 2]
    assert all(x["score"] == 0.9 for x in r)
    assert "rerank_score" not in HITS[0]


def test_diversity_soft_cap():
    r = select_ranked(HITS, [0.9, 0.8, 0.7, 0.6, 0.5], 3, 2)
    assert [x["document_id"] for x in r] == [1, 1, 2]
    assert len(select_ranked(HITS[:3], [0.9, 0.8, 0.7], 3, 1)) == 3


def test_validation_and_default_disabled():
    assert Query(query="VPN", knowledge_base_id=1).rerank is False
    with pytest.raises(ValidationError):
        Query(query="VPN", knowledge_base_id=1, top_k=5, candidate_k=3, rerank=True)
    with pytest.raises(ValidationError):
        Query(query="VPN", knowledge_base_id=1, max_per_document=2)


def test_invalid_score_count():
    with pytest.raises(ValueError):
        select_ranked(HITS, [1.0], 3)


def test_chat_retrieval_parameters_validated():
    from app.modules.chat.router import AskRequest

    assert AskRequest(question="VPN", knowledge_base_id=1).rerank is False
    with pytest.raises(ValidationError):
        AskRequest(question="VPN", knowledge_base_id=1, rerank=True, candidate_k=2, top_k=3)
