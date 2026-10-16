"""上传原创合成示例库并测真实召回；固定题集先验标注，不根据结果改题。

会创建并保留知识库，调用真实嵌入与 Milvus；--answers 还会调用在线 Qwen。
凭据仅从本地忽略 Git 的文件读取，不写入报告。
"""

import argparse
import hashlib
import json
import time

import httpx
from sqlalchemy import select

from app.core.config import ROOT, get_settings
from app.db.session import SessionLocal
from app.modules.auth.models import User
from app.modules.knowledge.models import Chunk, DocumentVersion

DATA = ROOT / "evals/qinglan"
STATE = ROOT / ".tmp/qinglan-import.json"


def normalize(text):
    return " ".join(text.split())


def score(hits, row, k):
    top = hits[:k]
    gold_docs = {fact["document_id"] for fact in row["evidence"]}
    found_docs = {hit["document_id"] for hit in top}
    facts = [
        any(
            hit["document_id"] == fact["document_id"]
            and normalize(fact["quote"]) in normalize(hit["content"])
            for hit in top
        )
        for fact in row["evidence"]
    ]
    return {
        "document_recall": len(gold_docs & found_docs) / len(gold_docs),
        "all_documents": gold_docs.issubset(found_docs),
        "evidence_recall": sum(facts) / len(facts),
        "all_evidence": all(facts),
        "facts_found": sum(facts),
        "facts_total": len(facts),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8010/api/v1")
    parser.add_argument("--answers", action="store_true", help="追加 5 道真实 Qwen 问答")
    parser.add_argument("--unified", action="store_true", help="对相同题集追加全部授权知识库检索")
    args = parser.parse_args()
    frozen = json.loads((DATA / "frozen-manifest.json").read_text())
    for name, value in frozen["sha256"].items():
        assert hashlib.sha256((DATA / name).read_bytes()).hexdigest() == value, (
            "Frozen data changed"
        )
    questions = json.loads((DATA / "questions.json").read_text())
    state = json.loads(STATE.read_text()) if STATE.exists() else {"documents": {}}
    credentials = json.loads((ROOT / ".tmp/local-admin-credentials.json").read_text())
    report = {
        "kind": "synthetic development retrieval evaluation, not blind",
        "frozen_sha256": frozen["sha256"],
        "positive": [],
        "negative": [],
        "answers": [],
    }
    settings = get_settings()
    report["retrieval_config"] = {
        "provider": settings.embedder_provider,
        "embedding_model": settings.embedding_model,
        "embedding_dim": settings.embedding_dim,
        "embedding_max_length": settings.embedding_max_length,
        "rerank": False,
        "top_k": 5,
        "llm_model": settings.llm_model,
    }
    client = httpx.Client(base_url=args.base_url, timeout=180)
    token = None

    def save():
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        STATE.chmod(0o600)

    def call(method, path, expected=200, **kwargs):
        response = client.request(
            method, path, headers={"Authorization": "Bearer " + token} if token else {}, **kwargs
        )
        assert response.status_code == expected, f"{method} {path}: HTTP {response.status_code}"
        return response.json() if response.content else None

    try:
        token = call("POST", "/auth/password/login", json=credentials)["token"]
        me = call("GET", "/auth/me")
        if "knowledge_base_id" not in state:
            kb = call(
                "POST",
                "/knowledge-bases",
                201,
                json={
                    "name": "青岚设备服务",
                    "description": "原创合成演示资料：Q2 巡检盒规格、联网、告警、售后、差旅、账号及数据管理。",
                },
            )
            state["knowledge_base_id"] = kb["id"]
            save()
        kb_id = state["knowledge_base_id"]
        for path in sorted((DATA / "corpus").glob("*.md")):
            if path.name in state["documents"]:
                continue
            result = call(
                "POST",
                f"/knowledge-bases/{kb_id}/documents",
                202,
                files={"file": (path.name, path.read_bytes())},
            )
            state["documents"][path.name] = result
            save()
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            documents = call("GET", f"/knowledge-bases/{kb_id}/documents?limit=100")
            assert not any(
                d["status"] == "failed" or d["index_status"] == "failed" for d in documents
            ), "Processing failure"
            if len(documents) == 8 and all(
                d["status"] == "parsed" and d["index_status"] == "indexed" for d in documents
            ):
                break
            time.sleep(2)
        else:
            raise RuntimeError("Processing timeout; created data retained for diagnosis")
        with SessionLocal() as db:
            users = [
                (u.email, u.role)
                for u in db.scalars(
                    select(User).where(
                        User.tenant_id == me["tenant_id"],
                        User.role != "admin",
                        User.is_active.is_(True),
                    )
                )
            ]
            version_ids = [d["version_id"] for d in state["documents"].values()]
            chunks = list(db.scalars(select(Chunk).where(Chunk.version_id.in_(version_ids))))
            report["chunk_count"] = len(chunks)
            report["chunk_policy"] = [
                {
                    "version_id": v.id,
                    "strategy": v.chunk_strategy,
                    "size": v.chunk_size,
                    "overlap": v.chunk_overlap,
                }
                for v in db.scalars(
                    select(DocumentVersion).where(DocumentVersion.id.in_(version_ids))
                )
            ]
        for email, role in users:
            call(
                "POST",
                f"/knowledge-bases/{kb_id}/members",
                201,
                json={"email": email, "role": "editor" if role == "editor" else "viewer"},
            )
        report["knowledge_base_id"] = kb_id
        for row in questions["positive"]:
            row = json.loads(json.dumps(row))
            for fact in row["evidence"]:
                fact["document_id"] = state["documents"][fact["file"]]["document_id"]
                version_id = state["documents"][fact["file"]]["version_id"]
                fact["gold_chunk_ids"] = [
                    c.id
                    for c in chunks
                    if c.version_id == version_id
                    and normalize(fact["quote"]) in normalize(c.content)
                ]
            start = time.perf_counter()
            result = call(
                "POST",
                "/search",
                json={"query": row["question"], "knowledge_base_id": kb_id, "top_k": 5},
            )
            row["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
            row["hits"] = result["hits"]
            row["metrics"] = {str(k): score(result["hits"], row, k) for k in [1, 3, 5]}
            row["reciprocal_rank"] = next(
                (
                    1 / (i + 1)
                    for i, h in enumerate(row["hits"])
                    if h["document_id"] in {f["document_id"] for f in row["evidence"]}
                ),
                0,
            )
            if args.unified:
                unified = call(
                    "POST", "/search", json={"query": row["question"], "scope": "all", "top_k": 5}
                )
                row["unified_hits"] = unified["hits"]
                row["unified_metrics"] = {str(k): score(unified["hits"], row, k) for k in [1, 3, 5]}
            report["positive"].append(row)
            print(
                row["id"],
                "document R@3",
                row["metrics"]["3"]["document_recall"],
                "evidence R@3",
                row["metrics"]["3"]["evidence_recall"],
                flush=True,
            )
        # 无答案题没有应召回证据，不能混进 Recall 的分母；仅保存其召回供观察。
        for row in questions["negative"]:
            result = call(
                "POST",
                "/search",
                json={"query": row["question"], "knowledge_base_id": kb_id, "top_k": 5},
            )
            report["negative"].append({**row, "hits": result["hits"]})
        rows = report["positive"]
        report["summary"] = {
            str(k): {
                "document_recall_macro": sum(r["metrics"][str(k)]["document_recall"] for r in rows)
                / len(rows),
                "all_documents_rate": sum(r["metrics"][str(k)]["all_documents"] for r in rows)
                / len(rows),
                "evidence_recall_macro": sum(r["metrics"][str(k)]["evidence_recall"] for r in rows)
                / len(rows),
                "all_evidence_rate": sum(r["metrics"][str(k)]["all_evidence"] for r in rows)
                / len(rows),
                "evidence_found": sum(r["metrics"][str(k)]["facts_found"] for r in rows),
                "evidence_total": sum(r["metrics"][str(k)]["facts_total"] for r in rows),
            }
            for k in [1, 3, 5]
        }
        if args.unified:
            report["unified_summary"] = {
                str(k): {
                    "document_recall_macro": sum(
                        r["unified_metrics"][str(k)]["document_recall"] for r in rows
                    )
                    / len(rows),
                    "evidence_recall_macro": sum(
                        r["unified_metrics"][str(k)]["evidence_recall"] for r in rows
                    )
                    / len(rows),
                    "all_evidence_rate": sum(
                        r["unified_metrics"][str(k)]["all_evidence"] for r in rows
                    )
                    / len(rows),
                    "evidence_found": sum(
                        r["unified_metrics"][str(k)]["facts_found"] for r in rows
                    ),
                    "evidence_total": sum(
                        r["unified_metrics"][str(k)]["facts_total"] for r in rows
                    ),
                }
                for k in [1, 3, 5]
            }
        report["mrr_at_5"] = sum(r["reciprocal_rank"] for r in rows) / len(rows)
        report["uncovered_evidence"] = [
            {"question_id": r["id"], "file": f["file"], "quote": f["quote"]}
            for r in rows
            for f in r["evidence"]
            if not f["gold_chunk_ids"]
        ]
        if args.answers:
            # 单事实、多事实、跨文档和无答案各有样例；按预先固定的编号抽测，不挑选召回赢家。
            for question_id in ["Q05", "Q14", "Q20", "Q23", "N01"]:
                row = next(
                    r
                    for r in questions["positive"] + questions["negative"]
                    if r["id"] == question_id
                )
                result = call(
                    "POST",
                    "/chat/ask",
                    json={"question": row["question"], "knowledge_base_id": kb_id, "top_k": 5},
                )
                report["answers"].append(
                    {
                        "id": question_id,
                        "question": row["question"],
                        "expected_answerable": question_id.startswith("Q"),
                        "response": result,
                    }
                )
                print(
                    "Answer", question_id, result["answerable"], result["answer_source"], flush=True
                )
        (DATA / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print("SUMMARY", json.dumps(report["summary"], ensure_ascii=False), flush=True)
    finally:
        if token:
            call("POST", "/auth/logout")
        client.close()


if __name__ == "__main__":
    main()
