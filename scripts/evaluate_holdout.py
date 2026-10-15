# 中文导读：
# 运行预先冻结的数据集评测
# 数据一旦被用于调试和方案选择，就不能继续把后续结果称为独立盲测

"""Prospectively frozen paired evaluation; no label edits or implicit retries."""

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
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.adapters.reranker.local import get_reranker, select_ranked
from app.core.config import ROOT, get_settings
from app.db.session import SessionLocal
from app.modules.chat.router import AskRequest, answer_question
from app.modules.knowledge.models import Document
from scripts.evaluate_v2 import Harness, corpus_sha256, git_info, percentile
from scripts.evidence_annotations import fact_coverage, normalize


def load_frozen():
    folder = ROOT / "evals/holdout"
    raw = (folder / "questions.json").read_bytes()
    protocol = json.loads((folder / "protocol.json").read_text())
    if hashlib.sha256(raw).hexdigest() != protocol["dataset_sha256"]:
        raise ValueError("Frozen questions changed; use a new protocol/version")
    questions = json.loads(raw)
    for q in questions:
        if q["kind"] == "answerable" and not q["fact_groups"]:
            raise ValueError("Missing answer evidence")
        for group in q["fact_groups"]:
            for option in group["options"]:
                source = ROOT / "evals/corpus" / q["domain"] / option["source"]
                if normalize(option["quote"]) not in normalize(source.read_text()):
                    raise ValueError(f"Unverified quote: {q['id']}")
    return questions, protocol


def summarize(rows):
    summary = {}
    for strategy in ["dense_3", "rerank_diverse_2"]:
        selected = [r for r in rows if r["strategy"] == strategy]
        answerable = [r for r in selected if r["kind"] == "answerable"]
        refusal = [r for r in selected if r["kind"] != "answerable"]
        summary[strategy] = {
            "completed_rows": len(selected),
            "errors": sum(bool(r.get("error")) for r in selected),
            "answerable_denominator": len(answerable),
            "complete_evidence_count": sum(r.get("evidence_complete", False) for r in answerable),
            "expected_refusal_denominator": len(refusal),
            "correct_refusal_count": sum(r.get("correct_refusal", False) for r in refusal),
            "cross_kb_leakage_count": sum(r.get("cross_kb_leakage", False) for r in selected),
            "citation_evidence_complete_count": sum(
                r.get("citation_evidence_complete", False) for r in answerable
            ),
            "generation_error_count": sum(bool(r.get("generation_error")) for r in selected),
            "retrieval_p50_ms": percentile(
                [r["retrieval_ms"] for r in selected if "retrieval_ms" in r], 0.5
            ),
            "rerank_p50_ms": percentile(
                [r["rerank_ms"] for r in selected if "rerank_ms" in r], 0.5
            ),
            "rerank_p95_ms": percentile(
                [r["rerank_ms"] for r in selected if "rerank_ms" in r], 0.95
            ),
            "independently_reviewed_answers": 0,
        }
    return summary


def main():
    questions, protocol = load_frozen()
    folder = (
        ROOT
        / "evals/holdout/runs"
        / datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
    )
    folder.mkdir(parents=True)
    settings = get_settings()
    payload = {
        "metadata": {
            "protocol": protocol,
            "corpus_sha256": corpus_sha256(),
            "git": git_info(),
            "llm_model": settings.llm_model,
            "reranker_model": settings.reranker_model,
            "max_length": settings.reranker_max_length,
            "batch_size": settings.reranker_batch_size,
        },
        "rows": [],
    }

    def save():
        payload["summary"] = summarize(payload["rows"])
        (folder / "results.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        )

    save()
    print("Run:", folder, flush=True)
    reranker = get_reranker()
    reranker.score("预热", [{"content": "预热模型"}])
    payload["metadata"]["device"] = reranker.device
    with httpx.Client(base_url="http://127.0.0.1:8010/api/v1", timeout=180) as client:
        harness = Harness(client, "synthetic-v1", True)
        harness.ensure_kbs()
        harness.wait_indexed(126, 120)
        payload["metadata"]["knowledge_base_ids"] = harness.kbs
        warm = questions[0]
        response = client.post(
            "/search",
            json={
                "query": warm["question"],
                "knowledge_base_id": harness.kbs[warm["domain"]],
                "top_k": 10,
            },
        )
        response.raise_for_status()
        for index, q in enumerate(questions):
            kb_id = harness.kbs[q.get("ask_domain", q["domain"])]
            try:
                started = perf_counter()
                response = client.post(
                    "/search",
                    json={"query": q["question"], "knowledge_base_id": kb_id, "top_k": 10},
                )
                response.raise_for_status()
                hits = response.json()["hits"]
                retrieval_ms = round((perf_counter() - started) * 1000, 2)
                started = perf_counter()
                scores = reranker.score(q["question"], hits)
                rerank_ms = round((perf_counter() - started) * 1000, 2)
                with SessionLocal() as db:
                    owners = dict(
                        db.execute(
                            select(Document.id, Document.knowledge_base_id).where(
                                Document.id.in_([h["document_id"] for h in hits])
                            )
                        ).all()
                    )
                strategies = [
                    ("dense_3", hits[:3]),
                    ("rerank_diverse_2", select_ranked(hits, scores, 3, 2)),
                ]
            except (httpx.HTTPError, SQLAlchemyError, ValueError, RuntimeError) as exc:
                for strategy in protocol["strategies"]:
                    payload["rows"].append({**q, "strategy": strategy, "error": type(exc).__name__})
                save()
                continue
            # Alternate first-call order to reduce systematic provider timing bias.
            for strategy, selected in strategies[:: (-1 if index % 2 else 1)]:
                row = {
                    **q,
                    "strategy": strategy,
                    "error": None,
                    "candidates": hits,
                    "reranker_scores": scores,
                    "selected_hits": selected,
                    "retrieval_ms": retrieval_ms,
                    "rerank_ms": rerank_ms if strategy != "dense_3" else 0,
                    "cross_kb_leakage": any(
                        owners.get(h["document_id"]) != kb_id for h in selected
                    ),
                    "human_correct": None,
                    "human_supported": None,
                }
                if q["kind"] == "answerable":
                    row["evidence_complete"] = fact_coverage(q["fact_groups"], selected)
                started = perf_counter()
                try:
                    result = answer_question(
                        AskRequest(question=q["question"], knowledge_base_id=kb_id, top_k=3),
                        selected,
                    )
                    row["generation"] = result
                    if q["kind"] == "answerable":
                        row["citation_evidence_complete"] = bool(
                            result["answerable"]
                        ) and fact_coverage(q["fact_groups"], result["citations"])
                    else:
                        row["correct_refusal"] = (
                            result["answerable"] is False and not result["citations"]
                        )
                except (HTTPException, ValueError, RuntimeError) as exc:
                    row["generation_error"] = type(exc).__name__
                    row["error"] = "generation_failed"
                row["generation_ms"] = round((perf_counter() - started) * 1000, 2)
                payload["rows"].append(row)
                save()
                print(q["id"], strategy, "error" if row["error"] else "ok", flush=True)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
