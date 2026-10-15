# 中文导读：
# 在相同候选池上比较排序策略，避免把召回候选差异误计为重排收益

"""Paired dev-only comparison: one candidate pool, one scoring pass, three selectors."""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from sqlalchemy import select

from app.adapters.reranker.local import get_reranker, select_ranked
from app.core.config import ROOT, get_settings
from app.db.session import SessionLocal
from app.modules.knowledge.models import Document
from scripts.evaluate_v2 import (
    Harness,
    corpus_sha256,
    evaluation_kind,
    evidence_metrics,
    git_info,
    summarize,
)


def main():
    raw = (ROOT / "evals/questions.json").read_bytes()
    questions = [q for q in json.loads(raw) if q["split"] == "dev"]
    s = get_settings()
    folder = (
        ROOT
        / "evals/reranker_runs"
        / datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
    )
    folder.mkdir(parents=True)
    payload = {
        "metadata": {
            "split": "dev",
            "candidate_k": 10,
            "top_k": 3,
            "dataset_sha256": hashlib.sha256(raw).hexdigest(),
            "corpus_sha256": corpus_sha256(),
            "metric_version": "evidence-v3",
            "model": s.reranker_model,
            "max_length": s.reranker_max_length,
            "batch_size": s.reranker_batch_size,
            "git_commit": git_info()[0],
        },
        "rows": [],
        "summary": {},
    }
    print("Run:", folder, flush=True)
    started = perf_counter()
    reranker = get_reranker()
    reranker.score("如何登录 VPN？", [{"content": "使用公司账号登录 VPN。"}])
    payload["metadata"].update(
        {
            "device": reranker.device,
            "model_load_and_warmup_ms": round((perf_counter() - started) * 1000, 2),
        }
    )
    with httpx.Client(base_url="http://127.0.0.1:8010/api/v1", timeout=180) as client:
        harness = Harness(client, "synthetic-v1", True)
        harness.ensure_kbs()
        harness.wait_indexed(126, 120)
        payload["metadata"]["knowledge_base_ids"] = harness.kbs
        # Warm embedding/API separately; measured retrieval includes the shared top-10 request.
        first = questions[0]
        r = client.post(
            "/search",
            json={
                "query": first["question"],
                "knowledge_base_id": harness.kbs[first.get("ask_domain") or first["domain"]],
                "top_k": 10,
            },
        )
        r.raise_for_status()
        for q in questions:
            started = perf_counter()
            kb_id = harness.kbs[q.get("ask_domain") or q["domain"]]
            response = client.post(
                "/search", json={"query": q["question"], "knowledge_base_id": kb_id, "top_k": 10}
            )
            response.raise_for_status()
            hits = response.json()["hits"]
            retrieval_ms = (perf_counter() - started) * 1000
            started = perf_counter()
            scores = reranker.score(q["question"], hits)
            rerank_ms = (perf_counter() - started) * 1000
            strategies = {
                "dense_3": hits[:3],
                "rerank_10_to_3": select_ranked(hits, scores, 3),
                "rerank_diverse_2": select_ranked(hits, scores, 3, 2),
            }
            with SessionLocal() as db:
                owners = dict(
                    db.execute(
                        select(Document.id, Document.knowledge_base_id).where(
                            Document.id.in_([h["document_id"] for h in hits])
                        )
                    ).all()
                )
            for strategy, selected in strategies.items():
                row = {
                    **q,
                    "evaluation_kind": evaluation_kind(q),
                    "strategy": strategy,
                    "retrieved_sources": [h["filename"] for h in selected],
                    "retrieved_chunk_ids": [h["chunk_id"] for h in selected],
                    "candidates": hits,
                    "reranker_scores": scores,
                    "selected_hits": selected,
                    "error": None,
                    "retrieval_ms": round(retrieval_ms, 2),
                    "rerank_ms": round(rerank_ms, 2) if strategy != "dense_3" else 0,
                    "pipeline_ms": round(
                        retrieval_ms + (rerank_ms if strategy != "dense_3" else 0), 2
                    ),
                    **evidence_metrics(q, selected),
                }
                if "isolation" in q:
                    row["cross_kb_leakage"] = any(
                        owners.get(h["document_id"]) != kb_id for h in selected
                    )
                payload["rows"].append(row)
            for strategy in strategies:
                rows = [r for r in payload["rows"] if r["strategy"] == strategy]
                payload["summary"][strategy] = summarize(rows, True)
            (folder / "results.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            )
            print(q["id"], f"rerank {rerank_ms:.0f}ms", flush=True)
    (folder / "metadata.json").write_text(
        json.dumps(payload["metadata"], ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
