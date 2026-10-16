"""召回指标必须区分找对文档和找全必要证据。"""

from scripts.evaluate_qinglan import score


def test_correct_document_wrong_passage_is_not_evidence_recall():
    row = {"evidence": [{"document_id": 1, "quote": "先验证再全量部署"}]}
    hits = [{"document_id": 1, "content": "设备支持无线联网"}]
    result = score(hits, row, 1)
    assert result["document_recall"] == 1
    assert result["evidence_recall"] == 0
    assert not result["all_evidence"]


def test_cross_document_question_needs_both_sources():
    row = {
        "evidence": [{"document_id": 1, "quote": "2.4 GHz"}, {"document_id": 2, "quote": "30 分钟"}]
    }
    hits = [
        {"document_id": 1, "content": "仅支持 2.4 GHz"},
        {"document_id": 2, "content": "首次响应 30 分钟"},
    ]
    assert score(hits, row, 1)["document_recall"] == 0.5
    assert score(hits, row, 1)["evidence_recall"] == 0.5
    assert not score(hits, row, 1)["all_documents"]
    assert score(hits, row, 2)["all_evidence"]


def test_same_quote_in_wrong_document_does_not_count():
    row = {"evidence": [{"document_id": 1, "quote": "最多 5000 条"}]}
    hits = [{"document_id": 2, "content": "最多 5000 条"}]
    assert score(hits, row, 5)["facts_found"] == 0


def test_layout_whitespace_is_allowed_but_missing_half_is_not():
    row = {
        "evidence": [{"document_id": 1, "quote": "30 分钟"}, {"document_id": 1, "quote": "24 小时"}]
    }
    hits = [{"document_id": 1, "content": "首次响应 30\n 分钟"}]
    result = score(hits, row, 1)
    assert result["evidence_recall"] == 0.5
    assert result["facts_found"] == 1 and result["facts_total"] == 2
