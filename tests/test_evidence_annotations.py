import json

import pytest

from app.core.config import ROOT
from scripts.evaluate_v2 import evidence_metrics
from scripts.evidence_annotations import fact_coverage, validate_annotations


def test_curated_quotes_exist_in_source():
    data = validate_annotations(ROOT / "evals")
    assert len(data["changes"]) == 7


def test_all_facts_required_and_sources_constrained():
    groups = [
        {"fact": "天数", "options": [{"source": "faq.md", "quote": "婚假10天"}]},
        {"fact": "期限", "options": [{"source": "faq.md", "quote": "12个月内"}]},
    ]
    assert not fact_coverage(groups, [{"filename": "faq.md", "content": "婚假10天"}])
    assert not fact_coverage(groups, [{"filename": "other.md", "content": "婚假10天，12个月内"}])
    assert fact_coverage(groups, [{"filename": "faq.md", "content": "婚假10天，12个月内"}])


def test_original_standard_remains_separate():
    questions = json.loads((ROOT / "evals/questions.json").read_text())
    q = next(q for q in questions if q["id"] == "HR-03")
    hit = {
        "filename": "员工关系与假期常见问题 FAQ.md",
        "content": "10 个自然日，须在领取结婚证之日起 12 个月内休完。",
    }
    result = evidence_metrics(q, [hit])
    assert result["evidence_complete_at_k"] is False
    assert result["accepted_evidence_complete_at_k"] is True


def test_hr32_supplement_has_both_sources():
    q = next(
        q for q in json.loads((ROOT / "evals/questions.json").read_text()) if q["id"] == "HR-32"
    )
    hits = [
        {
            "filename": "新员工试用期管理与转正流程.md",
            "content": "试用期届满前 10 个工作日启动转正评估。",
        },
        {
            "filename": "绩效考核管理办法.md",
            "content": "试用期员工在转正评估时单独使用《转正评估表》。入职不满 2 个月的员工不参与当季考核。",
        },
    ]
    result = evidence_metrics(q, hits)
    assert result["evidence_label_error"]
    assert result["accepted_evidence_label_error"] is None
    assert result["accepted_evidence_complete_at_k"] is True
    assert not evidence_metrics(q, hits[:1])["accepted_evidence_complete_at_k"]


def test_nonexistent_quote_rejected(tmp_path):
    folder = tmp_path / "corpus/it"
    folder.mkdir(parents=True)
    (folder / "source.md").write_text("原文")
    data = {
        "version": "test",
        "changes": {
            "Q": {
                "domain": "it",
                "fact_groups": [
                    {"fact": "事实", "options": [{"source": "source.md", "quote": "编造的证据"}]}
                ],
            }
        },
    }
    (tmp_path / "evidence_annotations.json").write_text(json.dumps(data))
    with pytest.raises(ValueError):
        validate_annotations(tmp_path)
