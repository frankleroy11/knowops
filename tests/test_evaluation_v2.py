from scripts import evaluate_v2 as ev


def test_first_rank_and_multi_source_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(ev, "EVALS", tmp_path)
    corpus = tmp_path / "corpus" / "it"
    corpus.mkdir(parents=True)
    (corpus / "a.md").write_text("甲证据")
    (corpus / "b.md").write_text("乙证据")
    q = {
        "id": "test",
        "domain": "it",
        "kind": "answerable",
        "expected_sources": ["a.md", "b.md"],
        "terms": ["甲证据", "乙证据"],
    }
    hits = [
        {"filename": "x.md", "content": "干扰"},
        {"filename": "a.md", "content": "甲证据"},
        {"filename": "b.md", "content": "乙证据"},
    ]
    result = ev.evidence_metrics(q, hits)
    assert result["chunk_recall_at_1"] is False
    assert result["evidence_complete_at_k"] is True
    assert result["mrr_at_k"] == 0.5
    q["expected_sources"] = ["a.md"]
    q["terms"] = ["甲证据"]
    assert ev.evidence_metrics(q, hits)["chunk_recall_at_1"] is False
    assert ev.evidence_metrics(q, hits[1:])["chunk_recall_at_1"] is True


def test_isolation_errors_and_denominators():
    rows = [
        {"kind": "answerable", "doc_recall_at_k": True},
        {"kind": "answerable", "error": "HTTP 503"},
        {"kind": "answerable", "isolation": {}, "correct_refusal": True, "cross_kb_leakage": False},
        {"kind": "refusal", "error": "timeout"},
    ]
    s = ev.summarize(rows, False)
    assert s["answerable_questions"] == 2
    assert s["refusal_questions"] == 2
    assert s["source_recall_at_k"] == 0.5
    assert s["refusal_accuracy"] == 0.5
    assert s["isolation_refusal_accuracy"] == 1
    assert s["isolation_leakage_rate"] == 0


def test_ndcg_penalizes_missing_sources():
    assert ev.ndcg([1, 0, 0], 3, 2) < 1
    assert ev.ndcg([1, 1, 0], 3, 2) == 1


def test_incomplete_source_annotations_are_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(ev, "EVALS", tmp_path)
    corpus = tmp_path / "corpus" / "it"
    corpus.mkdir(parents=True)
    (corpus / "a.md").write_text("甲证据")
    (corpus / "b.md").write_text("未标注的另一事实")
    question = {
        "id": "gap",
        "domain": "it",
        "kind": "answerable",
        "expected_sources": ["a.md", "b.md"],
        "terms": ["甲证据"],
    }
    row = {
        **question,
        **ev.evidence_metrics(
            question,
            [
                {"filename": "a.md", "content": "甲证据"},
                {"filename": "b.md", "content": "未标注的另一事实"},
            ],
        ),
    }
    assert row["doc_recall_at_k"] is True
    assert row["evidence_label_error"]
    summary = ev.summarize([row], True)
    assert summary["source_recall_at_k"] == 1
    assert summary["evidence_evaluable_questions"] == 0
    assert summary["evidence_complete_at_k"] is None
    assert "refusal_accuracy" not in summary
