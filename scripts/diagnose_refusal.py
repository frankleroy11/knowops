# 中文导读：
# 在固定证据上下文中诊断拒答与摘录匹配，输出用于排错，不自动更改标准答案

"""Bounded, secret-free diagnosis of model refusals on frozen context.

Replays the exact sources payload that a stored run already sent to Qwen
(no new retrieval, no ranking change), and archives the raw parsed model
response, including unanswered_questions, which the chat API currently
drops when the model refuses.

Usage:
    python scripts/diagnose_refusal.py --question-id NEW-09
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.adapters.llm.qwen import LLMUnavailable, generate_grounded_answer
from app.core.config import ROOT, get_settings

DEFAULT_RUN = "evals/context_runs/20261013-180519/results.json"
MAX_CALLS_HARD_LIMIT = 6


def build_sources(hits, limit=None):
    """Mirror app/modules/chat/router.py answer_question source construction."""
    selected = hits[:limit] if limit else hits
    return [
        {
            "id": i,
            "filename": h.get("filename", ""),
            "knowledge_base": h.get("knowledge_base_name", ""),
            "content": h["content"][:1200],
        }
        for i, h in enumerate(selected, 1)
    ]


def source_digest(source):
    return {
        "id": source["id"],
        "filename": source["filename"],
        "knowledge_base": source["knowledge_base"],
        "content_sha256": hashlib.sha256(source["content"].encode("utf-8")).hexdigest(),
        "content_chars": len(source["content"]),
    }


def quote_presence(fact_groups, sources):
    """Deterministic local check: which frozen evidence quotes are visible to the model."""
    normalized = [(s["id"], " ".join(s["content"].split())) for s in sources]
    rows = []
    for group in fact_groups:
        for option in group["options"]:
            quote = " ".join(option["quote"].split())
            visible = [sid for sid, text in normalized if quote in text]
            rows.append(
                {
                    "fact": group["fact"],
                    "source": option["source"],
                    "quote": option["quote"],
                    "visible_in_source_ids": visible,
                }
            )
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question-id", default="NEW-09")
    parser.add_argument("--run", default=DEFAULT_RUN, help="archived run to replay")
    parser.add_argument("--max-calls", type=int, default=MAX_CALLS_HARD_LIMIT)
    parser.add_argument("--label", default="diagnostic only, not a regression result")
    parser.add_argument(
        "--probe-question",
        action="append",
        default=[],
        help="narrower diagnostic question run on the same frozen sources; repeatable",
    )
    parser.add_argument(
        "--probe-strategy",
        default="anchors_3",
        help="which frozen strategy's sources the probes reuse",
    )
    args = parser.parse_args()

    archive_path = ROOT / args.run
    archive = json.loads(archive_path.read_text(encoding="utf-8"))
    rows = [row for row in archive["rows"] if row.get("id") == args.question_id]
    if not rows:
        raise SystemExit(f"{args.question_id} not found in {archive_path}")

    jobs = []
    if args.probe_question:
        base = next((r for r in rows if r["strategy"] == args.probe_strategy), None)
        if base is None:
            raise SystemExit(f"strategy {args.probe_strategy} not found for {args.question_id}")
        sources = build_sources(base["selected_hits"], limit=base.get("context_chunk_count"))
        for text in args.probe_question:
            jobs.append(
                {
                    "row": base,
                    "as_asked": text,
                    "strategy": f"probe:{args.probe_strategy}",
                    "sources": sources,
                }
            )
    else:
        for row in rows:
            jobs.append(
                {
                    "row": row,
                    "as_asked": row["question"],
                    "strategy": row["strategy"],
                    "sources": build_sources(
                        row["selected_hits"], limit=row.get("context_chunk_count")
                    ),
                }
            )

    budget = min(args.max_calls, MAX_CALLS_HARD_LIMIT)
    if len(jobs) > budget:
        raise SystemExit(f"needs {len(jobs)} calls, budget is {budget}")

    folder = (
        ROOT
        / "evals/answer_diagnostics"
        / datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
    )
    folder.mkdir(parents=True)
    payload = {
        "metadata": {
            "purpose": args.label,
            "question_id": args.question_id,
            "replay_source": args.run,
            "model": get_settings().llm_model,
            "temperature": 0,
            "calls_budget": budget,
            "probe_questions": args.probe_question,
            "counts_as_regression": False,
            "note": (
                "Sources reconstructed from the archived row; no retrieval re-run. "
                "unanswered_questions is retained here because the refusal path drops it."
            ),
        },
        "rows": [],
    }
    out = folder / "results.json"

    def save():
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    save()
    print("Diagnostics:", folder, flush=True)
    for job in jobs:
        row = job["row"]
        sources = job["sources"]
        record = {
            "id": row["id"],
            "frozen_question": row["question"],
            "as_asked": job["as_asked"],
            "is_frozen_question": job["as_asked"] == row["question"],
            "strategy": job["strategy"],
            "archived_grounding_status": row.get("generation", {}).get("grounding_status"),
            "context_chunk_count": len(sources),
            "sources": [source_digest(s) for s in sources],
            "evidence_quotes_visible": quote_presence(row["fact_groups"], sources),
        }
        started = perf_counter()
        try:
            raw = generate_grounded_answer(job["as_asked"], sources)
            record["raw_model_response"] = raw
            record["answerable"] = raw.get("answerable")
            record["claims_count"] = len(raw.get("claims") or [])
            record["model_unanswered_questions"] = raw.get("unanswered_questions")
            record["error"] = None
            status = f"answerable={raw.get('answerable')}"
        except LLMUnavailable as exc:
            record["error"] = str(exc)
            status = "LLMUnavailable"
        record["latency_ms"] = round((perf_counter() - started) * 1000, 2)
        payload["rows"].append(record)
        save()
        print(row["id"], job["strategy"], status, flush=True)
    print("Output:", out, flush=True)


if __name__ == "__main__":
    main()
