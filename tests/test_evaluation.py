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
    """新数据集（星桥科技合成语料）：题集必须与语料一致，且标注可被机械验证。"""
    root = Path(__file__).resolve().parents[1] / "evals"
    rows = json.loads((root / "questions.json").read_text(encoding="utf-8"))
    assert len(rows) == 168, "150 道主题 + 18 道跨库隔离题"
    assert len({r["id"] for r in rows}) == 168
    assert sum(r["kind"] == "answerable" for r in rows) == 120
    assert sum(r["kind"] == "refusal" for r in rows) == 48
    assert sum("isolation" in r for r in rows) == 18
    assert {r["split"] for r in rows} == {"dev", "test"}
    assert {r["domain"] for r in rows} == {"it", "hr", "product"}
    for row in rows:
        assert row["question"].strip()
        if row["kind"] == "refusal":
            assert row["expected_sources"] == []
            continue
        if "isolation" in row:
            # 跨库隔离题：提问所在库不该有答案，故 expected_sources 为空；
            # 答案出处记录在 expected_sources_in_source_kb，并且真的存在于源库。
            assert row["expected_sources"] == []
            assert row["ask_domain"] == row["isolation"]["ask_in"]
            assert row["isolation"]["answer_in"] == row["domain"]
            for filename in row["expected_sources_in_source_kb"]:
                path = root / "corpus" / row["domain"] / filename
                assert path.is_file(), f"{row['id']} 跨库题源文件缺失 {filename}"
            continue
        assert row["expected_sources"], row["id"]
        contents = []
        for filename in row["expected_sources"]:
            path = root / "corpus" / row["domain"] / filename
            assert path.is_file(), f"{row['id']} 缺少源文件 {filename}"
            contents.append(" ".join(path.read_text(encoding="utf-8").split()))
        blob = " ".join(contents)
        for term in row["terms"]:
            assert " ".join(str(term).split()) in blob, f"{row['id']} terms 未逐字命中：{term!r}"


def test_dataset_manifest_matches_corpus():
    """manifest.json 必须与当前语料一致，避免改了语料忘记重新装配题集。"""
    import hashlib

    root = Path(__file__).resolve().parents[1] / "evals"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    hashed = manifest["corpus"]["sha256"]
    files = sorted(
        path
        for domain in ("it", "hr", "product")
        for path in (root / "corpus" / domain).iterdir()
        if path.suffix.lower() in {".md", ".txt", ".pdf"}
    )
    assert len(files) == len(hashed) == manifest["corpus"]["files"]
    for path in files:
        key = f"{path.parent.name}/{path.name}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == hashed[key], key
    questions = (root / "questions.json").read_bytes()
    assert hashlib.sha256(questions).hexdigest() == manifest["questions"]["sha256"]
