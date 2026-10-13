"""Recalculate paired dev metrics on frozen candidates, without model calls."""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import ROOT
from scripts.evaluate_v2 import evidence_metrics, grouped, summarize
from scripts.evidence_annotations import validate_annotations


def main():
    evals = ROOT / "evals"
    annotations = validate_annotations(evals)
    questions = {q["id"]: q for q in json.loads((evals / "questions.json").read_text())}
    source = evals / "reranker_runs/20261013-160934/results.json"
    original = json.loads(source.read_text())
    window_path = None
    for p in sorted((evals / "window_runs").glob("*/results.json")):
        d = json.loads(p.read_text())
        if (
            d["metadata"].get("window_algorithm") == "pair-budget-checked-v2"
            and len(d["rows"]) == 146
        ):
            window_path = p
    if window_path is None:
        raise ValueError("Missing verified window experiment")
    windows = json.loads(window_path.read_text())
    folder = (
        evals
        / "annotation_runs"
        / datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
    )
    folder.mkdir(parents=True)
    payload = {
        "metadata": {
            "operation": "offline re-scoring only; no new retrieval or model inference",
            "metric_version": "evidence-v4-dual",
            "annotation_version": annotations["version"],
            "annotations_sha256": hashlib.sha256(
                (evals / "evidence_annotations.json").read_bytes()
            ).hexdigest(),
            "questions_sha256": hashlib.sha256((evals / "questions.json").read_bytes()).hexdigest(),
            "sources": {
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [source, window_path]
            },
        },
        "rows": [],
        "summary": {},
        "by_difficulty": {},
    }
    for old in original["rows"] + windows["rows"]:
        q = questions[old["id"]]
        assert q["split"] == "dev" and q["question"] == old["question"]
        # Preserve raw old metrics separately; never overwrite the historical report.
        row = {**old, **evidence_metrics(q, old["selected_hits"])}
        payload["rows"].append(row)
    for strategy in sorted({r["strategy"] for r in payload["rows"]}):
        rows = [r for r in payload["rows"] if r["strategy"] == strategy]
        assert len(rows) == 73
        payload["summary"][strategy] = summarize(rows, True)
        payload["by_difficulty"][strategy] = grouped(rows, "difficulty", True)
    (folder / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    lines = [
        "# 等价证据标注与冻结候选重评分",
        "",
        "本轮没有重新检索、调用 Qwen 或运行 test 集。73 道 dev 题、62 道实际有答案题，五种选择策略共享原实验候选。",
        "仅六道已复核 dev 题新增等价来源；HR-32 补充是客观标注修复，但它属于 test，因此不在本次 dev 对照中。",
        "原题集、facts、manifest 与历史报告未修改。评估附加标注单独版本化，原始严格指标保持不变。",
        "",
        "|方案|原标准完整证据覆盖|接受等价证据后的覆盖|",
        "|---|---|---|",
    ]
    for strategy, s in payload["summary"].items():
        lines.append(
            f"|{strategy}|{s['evidence_complete_at_k']:.2%}|{s['accepted_evidence_complete_at_k']:.2%}|"
        )
    lines += ["", "## 修改清单", ""]
    for id, entry in annotations["changes"].items():
        lines.append(f"- {id}：{entry['review_basis']}")
    lines += [
        "",
        "## 判定边界",
        "",
        "同一问题包含多个必需事实时，每个事实必须有已核对来源的完整证据片段，不能只匹配数字。",
        "允许任一标注明确等价的来源支持一个事实；不允许任意包含相同措辞的文件自动成为正确来源。",
        "这是经过诊断后修订的标注，属于开发探索；指标变化不能解释为模型能力提升。",
        "不报告回答正确率，也不把助手复核等同于独立人工标注。后续需要人工确认和新盲测集。",
        "候选、重排分数与耗时来自原实验，本轮只重算标签，不能将历史耗时称为新测量。",
        "",
        "## 默认方案",
        "",
        "是否采用重排，应比较同一新版口径下不同方案的净收益，并结合实际增量耗时。",
        "即使新版证据覆盖提高，仍需独立新题集及生成质量验证后才能改默认方案。",
        "",
        f"完整逐题数据：`{folder.relative_to(ROOT)}/results.json`",
    ]
    text = "\n".join(lines) + "\n"
    (folder / "report.md").write_text(text)
    (ROOT / "docs/evidence-annotation-review.md").write_text(text)
    print(folder)
    for k, s in payload["summary"].items():
        print(k, s["evidence_complete_at_k"], s["accepted_evidence_complete_at_k"])


if __name__ == "__main__":
    main()
