# 中文导读：
# 分析已保存候选的重排表现与文本窗口，属于开发诊断，不能据此宣称独立盲测效果

"""Audit stored dev candidates and compare label-independent token-window scoring."""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.adapters.reranker.local import get_reranker, select_ranked
from app.core.config import ROOT
from scripts.evaluate_v2 import evidence_metrics, grouped, normalize, percentile, summarize


def token_windows(tokenizer, question, content, max_length=512, overlap=64):
    budget = (
        max_length
        - len(tokenizer(question, add_special_tokens=False)["input_ids"])
        - tokenizer.num_special_tokens_to_add(pair=True)
    )
    if budget <= overlap:
        raise ValueError("Question too long for window budget")
    encoded = tokenizer(content, add_special_tokens=False, return_offsets_mapping=True)
    offsets = encoded["offset_mapping"]
    if not offsets:
        return [""]
    windows = []
    start = 0
    while start < len(offsets):
        end = min(start + budget, len(offsets))
        while end > start:
            view = content[offsets[start][0] : offsets[end - 1][1]]
            if len(tokenizer(question, view, truncation=False)["input_ids"]) <= max_length:
                break
            end -= 1
        if end <= start:
            raise ValueError("Cannot fit a document token into the pair budget")
        windows.append(view)
        if end == len(offsets):
            break
        start = max(start + 1, end - overlap)

    return windows


def main():
    source = ROOT / "evals/reranker_runs/20261013-160934/results.json"
    original = json.loads(source.read_text())
    reranker = get_reranker()
    tokenizer = reranker.model.tokenizer
    folder = (
        ROOT
        / "evals/window_runs"
        / datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
    )
    folder.mkdir(parents=True)
    payload = {
        "metadata": {
            "source": str(source.relative_to(ROOT)),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "split": "dev",
            "model": reranker.model_name,
            "device": reranker.device,
            "max_length": 512,
            "overlap_tokens": 64,
            "aggregation": "max",
            "window_algorithm": "pair-budget-checked-v2",
            "note": "Windows use only question and candidate text; labels used only for evaluation.",
        },
        "rows": [],
        "audit": [],
        "summary": {},
    }
    by_strategy = {}
    for row in original["rows"]:
        by_strategy.setdefault(row["strategy"], {})[row["id"]] = row
    dense = by_strategy["dense_3"]
    previous = by_strategy["rerank_10_to_3"]
    reranker.score("VPN", [{"content": "VPN 登录指南"}])
    print("Run:", folder, flush=True)
    for id, row in dense.items():
        candidates = row["candidates"]
        q = row["question"]
        views = []
        owners = []
        diagnostics = []
        for i, hit in enumerate(candidates):
            full = normalize(hit["content"])
            encoded = tokenizer(
                q,
                hit["content"],
                truncation="longest_first",
                max_length=512,
                return_offsets_mapping=True,
            )
            ends = [
                off[1]
                for off, seq in zip(encoded["offset_mapping"], encoded.sequence_ids(), strict=True)
                if seq == 1
            ]
            cutoff = max(ends, default=0)
            kept = normalize(hit["content"][:cutoff])
            actual = reranker.model.preprocess([(q, hit["content"])])["input_ids"][0].tolist()
            assert actual == encoded["input_ids"], (
                "Audit tokenizer does not match actual model preprocessing"
            )
            terms = [
                normalize(t)
                for t in row.get("terms", [])
                if normalize(t) in full and hit["filename"] in row["expected_sources"]
            ]
            lost = [t for t in terms if t not in kept]
            windows = token_windows(tokenizer, q, hit["content"])
            diagnostics.append(
                {
                    "chunk_id": hit["chunk_id"],
                    "filename": hit["filename"],
                    "original_dense_rank": i + 1,
                    "original_rerank_rank": 1
                    + sorted(
                        range(len(candidates)),
                        key=lambda j: row["reranker_scores"][j],
                        reverse=True,
                    ).index(i),
                    "pair_tokens": len(tokenizer(q, hit["content"], truncation=False)["input_ids"]),
                    "cutoff_character": cutoff,
                    "truncated": len(tokenizer(q, hit["content"], truncation=False)["input_ids"])
                    > 512,
                    "lost_marked_terms": lost,
                    "windows": len(windows),
                }
            )
            for text in windows:
                views.append({"content": text})
                owners.append(i)
        start = perf_counter()
        window_scores = reranker.score(q, views)
        scores = [float("-inf")] * len(candidates)
        for owner, score in zip(owners, window_scores, strict=True):
            scores[owner] = max(scores[owner], score)
        elapsed = (perf_counter() - start) * 1000
        audit = {
            "id": id,
            "question": q,
            "regressed": bool(row.get("evidence_complete_at_k"))
            and not previous[id].get("evidence_complete_at_k"),
            "candidates": diagnostics,
        }
        payload["audit"].append(audit)
        for strategy, cap in [("window_max", 0), ("window_max_diverse_2", 2)]:
            hits = select_ranked(candidates, scores, 3, cap)
            result = {
                **row,
                "strategy": strategy,
                "retrieved_sources": [h["filename"] for h in hits],
                "retrieved_chunk_ids": [h["chunk_id"] for h in hits],
                "selected_hits": hits,
                "window_scores": scores,
                "rerank_ms": round(elapsed, 2),
                "window_pair_count": len(views),
                **evidence_metrics(row, hits),
            }
            payload["rows"].append(result)
        for strategy in ["window_max", "window_max_diverse_2"]:
            rows = [r for r in payload["rows"] if r["strategy"] == strategy]
            payload["summary"][strategy] = summarize(rows, True)
        (folder / "results.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        )
        print(id, "windows", len(views), f"{elapsed:.0f}ms", flush=True)
    payload["by_difficulty"] = {
        strategy: grouped(
            [r for r in payload["rows"] if r["strategy"] == strategy], "difficulty", True
        )
        for strategy in payload["summary"]
    }
    payload["timing_summary"] = {
        strategy: {
            "p50_ms": percentile(
                [r["rerank_ms"] for r in payload["rows"] if r["strategy"] == strategy], 0.5
            ),
            "p95_ms": percentile(
                [r["rerank_ms"] for r in payload["rows"] if r["strategy"] == strategy], 0.95
            ),
        }
        for strategy in payload["summary"]
    }
    (folder / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
