# 中文导读：
# 对重排后的回答进行开发诊断；模型回答对照不等于经过人工标注的准确率评估

"""Diagnostic generation comparison on dev regression cases; not an accuracy benchmark."""

import json
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import ROOT, get_settings
from app.modules.chat.router import AskRequest, answer_question


def main():
    source = ROOT / "evals/reranker_runs/20261013-160934/results.json"
    original = json.loads(source.read_text())
    dense = {r["id"]: r for r in original["rows"] if r["strategy"] == "dense_3"}
    reranked = {r["id"]: r for r in original["rows"] if r["strategy"] == "rerank_10_to_3"}
    folder = (
        ROOT
        / "evals/answer_diagnostics"
        / datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
    )
    folder.mkdir(parents=True)
    payload = {
        "metadata": {
            "model": get_settings().llm_model,
            "split": "dev",
            "selection": "six evidence-coverage regressions, diagnostic only",
            "source": str(source.relative_to(ROOT)),
        },
        "rows": [],
    }
    for id, row in dense.items():
        if not row.get("evidence_complete_at_k") or reranked[id].get("evidence_complete_at_k"):
            continue
        for strategy, selected in [("dense_3", row), ("rerank_10_to_3", reranked[id])]:
            started = perf_counter()
            result = answer_question(
                AskRequest(question=row["question"], knowledge_base_id=1, top_k=3),
                selected["selected_hits"],
            )
            payload["rows"].append(
                {
                    "id": id,
                    "question": row["question"],
                    "reference_answer": row["reference_answer"],
                    "strategy": strategy,
                    "elapsed_ms": round((perf_counter() - started) * 1000, 2),
                    "human_correct": None,
                    "human_supported": None,
                    **result,
                }
            )
            (folder / "results.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            )
            print(id, strategy, result["answer"], flush=True)
    print("Output:", folder, flush=True)


if __name__ == "__main__":
    main()
