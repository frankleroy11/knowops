import json

import pytest

from scripts import evaluate_holdout as runner


def test_frozen_questions_are_grounded_and_balanced():
    questions, protocol = runner.load_frozen()
    assert len(questions) == protocol["questions"] == 18
    assert {
        kind: sum(q["kind"] == kind for q in questions)
        for kind in ["answerable", "refusal", "isolation"]
    } == {"answerable": 12, "refusal": 3, "isolation": 3}
    assert len({q["id"] for q in questions}) == len(questions)


def test_modified_frozen_dataset_is_rejected(tmp_path, monkeypatch):
    folder = tmp_path / "evals/holdout"
    folder.mkdir(parents=True)
    (folder / "questions.json").write_text("[]")
    (folder / "protocol.json").write_text(json.dumps({"dataset_sha256": "incorrect"}))
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="Frozen questions changed"):
        runner.load_frozen()


def test_failures_stay_in_denominators():
    result = runner.summarize(
        [
            {"strategy": "dense_3", "kind": "answerable", "error": "Timeout"},
            {
                "strategy": "dense_3",
                "kind": "refusal",
                "error": "generation_failed",
                "generation_error": "HTTPException",
            },
            {
                "strategy": "dense_3",
                "kind": "isolation",
                "error": None,
                "correct_refusal": True,
                "cross_kb_leakage": True,
            },
        ]
    )["dense_3"]
    assert result["answerable_denominator"] == 1
    assert result["complete_evidence_count"] == 0
    assert result["expected_refusal_denominator"] == 2
    assert result["correct_refusal_count"] == 1
    assert result["cross_kb_leakage_count"] == 1
    assert result["errors"] == 2
