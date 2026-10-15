# 中文导读：
# 使用冻结上下文回放引用校验，检查答案处理的开发回归；不能替代真实检索的端到端评测

"""Replay frozen contexts through the current answer pipeline; development regression only."""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException

from app.core.config import ROOT, get_settings
from app.modules.chat.router import AskRequest, answer_question
from scripts.evidence_annotations import fact_coverage


def main():
    source = ROOT / "evals/holdout/runs/20261013-165237/results.json"
    original = json.loads(source.read_text())
    folder = (
        ROOT
        / "evals/citation_runs"
        / datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
    )
    folder.mkdir(parents=True)
    payload = {
        "metadata": {
            "source": str(source.relative_to(ROOT)),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "selection": "All 36 frozen contexts; already diagnosed development regression, not new blind test",
            "llm_model": get_settings().llm_model,
            "pipeline_sha256": {
                name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                for name in ["app/modules/chat/router.py", "app/adapters/llm/qwen.py"]
            },
        },
        "rows": [],
    }
    for old in original["rows"]:
        row = {
            k: old[k]
            for k in ["id", "kind", "question", "strategy", "reference_answer", "fact_groups"]
        }
        row.update(
            selected_hits=old["selected_hits"],
            baseline_generation=old["generation"],
            human_correct=None,
            human_supported=None,
            error=None,
        )
        started = perf_counter()
        try:
            result = answer_question(
                AskRequest(question=old["question"], knowledge_base_id=1, top_k=3),
                old["selected_hits"],
            )
            row["generation"] = result
            if old["kind"] == "answerable":
                row["citation_evidence_complete"] = result["answerable"] and fact_coverage(
                    old["fact_groups"], result["citations"]
                )
            else:
                row["correct_refusal"] = not result["answerable"] and not result["citations"]
        except HTTPException as exc:
            row["error"] = f"HTTP {exc.status_code}"
        row["elapsed_ms"] = round((perf_counter() - started) * 1000, 2)
        payload["rows"].append(row)
        (folder / "results.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        )
        print(
            old["id"],
            old["strategy"],
            row.get("generation", {}).get("grounding_status", row["error"]),
            flush=True,
        )
    print("Output:", folder, flush=True)


if __name__ == "__main__":
    main()
