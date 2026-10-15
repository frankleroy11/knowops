# 中文导读：
# 比较相同召回锚点有无相邻块扩展时的表现，关注上下文补充对答案与证据的影响

"""Paired development regression: same live search anchors, with/without adjacent context."""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from fastapi import HTTPException

from app.core.config import ROOT, get_settings
from app.db.session import SessionLocal
from app.modules.chat.router import AskRequest, answer_question
from app.modules.retrieval.context import expand_neighbors
from scripts.evaluate_holdout import load_frozen
from scripts.evaluate_v2 import Harness, corpus_sha256, git_info
from scripts.evidence_annotations import fact_coverage


def main():
    questions, protocol = load_frozen()
    folder = (
        ROOT
        / "evals/context_runs"
        / datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
    )
    folder.mkdir(parents=True)
    payload = {
        "metadata": {
            "protocol": protocol,
            "purpose": "Already diagnosed development regression; not independent blind test",
            "git": git_info(),
            "corpus_sha256": corpus_sha256(),
            "llm_model": get_settings().llm_model,
            "code_sha256": {
                name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                for name in [
                    "app/modules/chat/router.py",
                    "app/adapters/llm/qwen.py",
                    "app/modules/retrieval/context.py",
                ]
            },
        },
        "rows": [],
    }

    def save():
        (folder / "results.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        )

    save()
    print("Run:", folder, flush=True)
    with httpx.Client(base_url="http://127.0.0.1:8010/api/v1", timeout=180) as client:
        harness = Harness(client, "synthetic-v1", True)
        harness.ensure_kbs()
        harness.wait_indexed(126, 120)
        payload["metadata"]["knowledge_base_ids"] = harness.kbs
        for index, q in enumerate(questions):
            kb_id = harness.kbs[q.get("ask_domain", q["domain"])]
            response = client.post(
                "/search", json={"query": q["question"], "knowledge_base_id": kb_id, "top_k": 3}
            )
            response.raise_for_status()
            anchors = response.json()["hits"]
            started = perf_counter()
            with SessionLocal() as db:
                expanded = expand_neighbors(anchors, db)
            expansion_ms = round((perf_counter() - started) * 1000, 2)
            assert all(h["knowledge_base_id"] == kb_id for h in expanded)
            strategies = [("anchors_3", False, anchors), ("neighbors_8", True, expanded)]
            for strategy, expand, hits in strategies[:: (-1 if index % 2 else 1)]:
                row = {
                    **q,
                    "strategy": strategy,
                    "anchors": anchors,
                    "selected_hits": hits,
                    "expansion_ms": expansion_ms if expand else 0,
                    "context_chunk_count": len(hits),
                    "error": None,
                    "human_correct": None,
                    "human_supported": None,
                    "cross_kb_leakage": False,
                }
                if q["kind"] == "answerable":
                    row["evidence_complete"] = fact_coverage(q["fact_groups"], hits)
                started = perf_counter()
                try:
                    result = answer_question(
                        AskRequest(
                            question=q["question"],
                            knowledge_base_id=kb_id,
                            top_k=3,
                            expand_context=expand,
                        ),
                        hits,
                    )
                    row["generation"] = result
                    if q["kind"] == "answerable":
                        row["citation_evidence_complete"] = result["answerable"] and fact_coverage(
                            q["fact_groups"], result["citations"]
                        )
                    else:
                        row["correct_refusal"] = (
                            not result["answerable"] and not result["citations"]
                        )
                except HTTPException as exc:
                    row["error"] = f"HTTP {exc.status_code}"
                row["generation_ms"] = round((perf_counter() - started) * 1000, 2)
                payload["rows"].append(row)
                save()
                print(
                    q["id"],
                    strategy,
                    row.get("generation", {}).get("grounding_status", row["error"]),
                    flush=True,
                )
    print("Output:", folder, flush=True)


if __name__ == "__main__":
    main()
