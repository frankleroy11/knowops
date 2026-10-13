"""Reproducible small-sample RAG evaluation. Creates and retains isolated demo data."""

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from app.adapters.vectorstore.milvus import collection_name
from app.core.config import ROOT, get_settings


def percentile(values, quantile):
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(quantile * len(ordered)) - 1)], 2)


def summarize(rows):
    answered = [r for r in rows if r["kind"] == "answerable"]
    refused = [r for r in rows if r["kind"] != "answerable"]
    successful = [r for r in rows if not r.get("error")]

    def rate(group, key):
        return round(sum(bool(r.get(key)) for r in group) / len(group), 4) if group else None

    return {
        "questions": len(rows),
        "successful_requests": len(successful),
        "answerable_questions": len(answered),
        "refusal_questions": len(refused),
        "source_recall_at_3": rate(answered, "retrieval_hit"),
        "refusal_accuracy": rate(refused, "correct_refusal"),
        "answerable_response_rate": rate(answered, "answerable"),
        "citation_source_match_rate": rate(answered, "citation_match"),
        "keyword_pass_rate_heuristic_only": rate(answered, "keyword_pass"),
        "timings_ms": {
            stage: {
                "p50": percentile(
                    [
                        r["timings_ms"][stage]
                        for r in successful
                        if stage in r.get("timings_ms", {})
                    ],
                    0.5,
                ),
                "p95": percentile(
                    [
                        r["timings_ms"][stage]
                        for r in successful
                        if stage in r.get("timings_ms", {})
                    ],
                    0.95,
                ),
            }
            for stage in ["retrieval", "generation", "total"]
        },
    }


def prepare(client, folder):
    ids = {}
    for label in ["主评估库", "隔离评估库"]:
        r = client.post(
            "/knowledge-bases",
            json={
                "name": f"评估-{folder.name}-{label}",
                "description": "固定合成测试资料，非真实企业制度",
            },
        )
        r.raise_for_status()
        ids[label] = r.json()["id"]
    for file in sorted((ROOT / "evals/corpus").glob("*.md")):
        kb = ids["隔离评估库" if file.name == "隔离库专用.md" else "主评估库"]
        r = client.post(
            f"/knowledge-bases/{kb}/documents",
            files={"file": (file.name, file.read_bytes(), "text/markdown")},
        )
        r.raise_for_status()
        if not r.json()["queued"]:
            raise RuntimeError("Upload persisted but parsing task was not queued")
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        docs = []
        for kb in ids.values():
            r = client.get(f"/knowledge-bases/{kb}/documents")
            r.raise_for_status()
            docs.extend(r.json())
        if any(d["status"] == "failed" or d["index_status"] == "failed" for d in docs):
            raise RuntimeError("Corpus parse or indexing failed; inspect document status")
        if len(docs) == 6 and all(d["index_status"] == "indexed" for d in docs):
            return ids
        time.sleep(2)
    raise RuntimeError("Corpus indexing timed out")


def report(folder, payload):
    (folder / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    lines = [
        "# KnowOps 固定评估集基线",
        "",
        "本次使用合成测试资料，样本量 30；不能代表真实企业数据或生产性能。",
        "",
        "指标按全部对应题目计算，HTTP 错误计为失败。Recall@3 为来源文档级命中（不是切片级）；",
        "关键词结果仅作筛查，不等同于回答正确率。耗时包含本机负载与模型冷启动。",
        "",
        "## 自动指标",
        "",
        "```json",
        json.dumps(payload["summary"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## 逐题结果",
        "",
        "|题号|类型|检索命中|正确拒答|引用匹配|关键词筛查|",
        "|---|---|---|---|---|---|",
    ]
    for r in payload["rows"]:
        lines.append(
            "|"
            + "|".join(
                str(r.get(k, "-"))
                for k in [
                    "id",
                    "kind",
                    "retrieval_hit",
                    "correct_refusal",
                    "citation_match",
                    "keyword_pass",
                ]
            )
            + "|"
        )
    lines += [
        "",
        "## 人工复核",
        "",
        "逐题审查答案正确性、原文支持程度与多余断言。未复核题目的人工分数保持为空。",
        "",
    ]
    for r in payload["rows"]:
        lines += [
            f"### {r['id']} {r['question']}",
            "",
            f"参考：{r['reference_answer']}",
            "",
            f"实际：{r.get('answer', '请求失败')}",
            "",
            f"来源：{', '.join(r.get('citation_filenames', [])) or '无'}",
            "",
            "人工结论：待复核",
            "",
        ]
    (folder / "report.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8010/api/v1")
    args = parser.parse_args()
    stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
    folder = ROOT / "evals/runs" / stamp
    folder.mkdir(parents=True)
    raw = (ROOT / "evals/questions.json").read_bytes()
    questions = json.loads(raw)
    s = get_settings()
    metadata = {
        "timestamp": stamp,
        "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "corpus_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "evals/corpus").glob("*.md"))
        },
        "model": s.llm_model,
        "embedding_model": s.embedding_model,
        "collection": collection_name(),
        "top_k": 3,
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        ),
    }
    payload = {"metadata": metadata, "rows": [], "summary": {}}
    (folder / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    print("Run:", folder, flush=True)
    with httpx.Client(base_url=args.base_url, timeout=180) as client:
        metadata["knowledge_bases"] = prepare(client, folder)
        for q in questions:
            row = {**q, "human_correct": None, "human_supported": None}
            kb = metadata["knowledge_bases"]["主评估库"]
            try:
                retrieved = client.post(
                    "/search", json={"query": q["question"], "knowledge_base_id": kb, "top_k": 3}
                )
                retrieved.raise_for_status()
                hits = retrieved.json()["hits"]
                row["retrieved_sources"] = [h["filename"] for h in hits]
                expected = set(q["expected_sources"])
                if expected:
                    row["retrieval_hit"] = expected.issubset(set(row["retrieved_sources"]))
                response = client.post(
                    "/chat/ask",
                    json={"question": q["question"], "knowledge_base_id": kb, "top_k": 3},
                )
                response.raise_for_status()
                answer = response.json()
                row.update(answer)
                cited = [h["filename"] for h in answer["citations"]]
                row["citation_filenames"] = cited
                if expected:
                    row["citation_match"] = (
                        bool(cited)
                        and expected.issubset(set(cited))
                        and set(cited).issubset(expected)
                    )
                    row["keyword_pass"] = answer["answerable"] and all(
                        k.casefold() in answer["answer"].casefold() for k in q["keywords"]
                    )
                else:
                    row["correct_refusal"] = (
                        answer["answerable"] is False and not answer["citations"]
                    )
            except httpx.HTTPError as error:
                row["error"] = (
                    f"HTTP status {error.response.status_code}"
                    if isinstance(error, httpx.HTTPStatusError)
                    else type(error).__name__
                )
            payload["rows"].append(row)
            payload["summary"] = summarize(payload["rows"])
            report(folder, payload)
            print(q["id"], "ERROR" if row.get("error") else "done", flush=True)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
