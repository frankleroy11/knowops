"""Feedback → regression candidate transformation (pure functions + frozen-set guard)."""

from datetime import datetime, timedelta
from types import SimpleNamespace

from app.core.config import ROOT
from scripts.feedback_to_regression import (
    collect_candidates,
    is_frozen,
    merge_candidates,
)

NOW = datetime(2026, 10, 15, 10, 0, 0)


def row(question, reason="", status="model_refused", minutes=0, kb=None, citations=0):
    return SimpleNamespace(
        question=question,
        reason=reason,
        grounding_status=status,
        citation_count=citations,
        knowledge_base_id=kb,
        created_at=NOW + timedelta(minutes=minutes),
    )


def test_collect_groups_by_question_and_keeps_the_newest_complaint():
    candidates = collect_candidates(
        [
            row("VPN 怎么申请？", reason="旧原因", minutes=0),
            row("VPN   怎么申请？", reason="新原因", minutes=5, citations=2),
        ]
    )
    assert len(candidates) == 1
    entry = candidates[0]
    assert entry["question"] == "VPN 怎么申请？"
    assert entry["feedback_count"] == 2
    assert entry["reason"] == "新原因"
    assert entry["citation_count"] == 2
    assert entry["first_seen"] < entry["last_seen"]
    assert entry["review_status"] == "pending" and entry["source"] == "feedback"


def test_blank_questions_are_skipped_and_output_is_sorted():
    candidates = collect_candidates([row("  "), row("b 问题"), row("a 问题")])
    assert [c["question"] for c in candidates] == ["a 问题", "b 问题"]


def test_merge_adds_new_and_refreshes_counts_without_losing_review_state():
    existing = [
        {
            "question": "old 问题",
            "feedback_count": 1,
            "review_status": "accepted",
            "reviewed_by": "pm",
            "reason": "旧原因",
            "last_seen": "2026-10-01T00:00:00",
        }
    ]
    incoming = collect_candidates([row("old 问题", reason="新原因", minutes=10), row("new 问题")])
    merged, added = merge_candidates(existing, incoming)
    assert added == 1
    by_question = {c["question"]: c for c in merged}
    assert by_question["old 问题"]["review_status"] == "accepted"  # 人工结论保留
    assert by_question["old 问题"]["reviewed_by"] == "pm"
    assert by_question["old 问题"]["reason"] == "新原因"  # 事实字段刷新
    assert by_question["old 问题"]["feedback_count"] == 1
    assert by_question["new 问题"]["review_status"] == "pending"
    assert [c["question"] for c in merged] == ["new 问题", "old 问题"]


def test_frozen_eval_sets_are_protected():
    assert is_frozen(ROOT / "evals" / "questions.json")
    assert is_frozen(ROOT / "evals" / "holdout" / "questions.json")
    assert not is_frozen(ROOT / "evals" / "regressions" / "feedback_candidates.json")
