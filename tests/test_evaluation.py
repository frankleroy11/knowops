import json
from pathlib import Path

from scripts.evaluate import percentile, summarize


def test_failures_remain_in_denominator():
    result = summarize(
        [
            {"kind": "answerable", "retrieval_hit": True, "citation_match": True},
            {"kind": "answerable", "error": "HTTP status 503"},
            {"kind": "unanswerable", "correct_refusal": True},
            {"kind": "isolation", "error": "ReadTimeout"},
        ]
    )
    assert result["source_recall_at_3"] == 0.5
    assert result["refusal_accuracy"] == 0.5
    assert result["successful_requests"] == 2
    assert result["timings_ms"]["total"]["p95"] is None


def test_nearest_rank_percentiles():
    assert percentile([4, 1, 3, 2], 0.5) == 2
    assert percentile([4, 1, 3, 2], 0.95) == 4
    assert percentile([], 0.95) is None


def test_fixed_dataset_has_source_files():
    root = Path(__file__).resolve().parents[1] / "evals"
    rows = json.loads((root / "questions.json").read_text())
    assert len(rows) == 30
    assert len({r["id"] for r in rows}) == 30
    assert sum(r["kind"] == "answerable" for r in rows) == 20
    assert sum(r["kind"] == "isolation" for r in rows) == 2
    for row in rows:
        for filename in row["expected_sources"]:
            assert (root / "corpus" / filename).is_file()
