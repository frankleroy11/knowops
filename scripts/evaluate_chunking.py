"""Paired synthetic development comparison; two enforced APIs differing only in CHUNK_STRATEGY.

Requires a running real Worker and BGE-M3/Milvus/Qwen. Temporary tenant data is
removed and baseline counts/files/vectors verified. Never uses business documents.
"""

import argparse
import hashlib
import json
import secrets
import subprocess
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import delete, func, select

from app.adapters.storage import LocalStorage
from app.adapters.vectorstore.milvus import MilvusStore
from app.core.config import ROOT, get_settings
from app.db.session import Base, SessionLocal
from app.main import app  # noqa: F401
from app.modules.audit.models import AuditLog
from app.modules.auth.models import ApiToken, User
from app.modules.auth.security import hash_token
from app.modules.ingestion.parser import parse_chunks
from app.modules.knowledge.models import Chunk, DocumentVersion, VectorIndex
from app.modules.tenant.models import Tenant


def dataset():
    clause = (
        "白鹭专项审批：费用不超过 128 元时，"
        + "提交的材料应当包括签字原件及对应的付款凭证，" * 6
        + "必须由部门负责人批准。"
    )
    prefix = "# 专项审批\n\n" + "背景说明仅供阅读，不作为审批依据。" * 38
    prefix = prefix[:650].ljust(650, "背") + "\n\n"
    table = "| 套餐 | 容量 | 保留期 |\n| --- | --- | --- |\n" + "| 标准套餐 | 20 GB | 30 天 |\n" * 8
    table_prefix = ("普通服务说明。" * 100)[:650].ljust(650, "说") + "\n\n"
    policy = "# 午餐制度\n\n白鹭验收计划员工午餐报销上限为每人每天 128 元。必须提交电子发票。"
    return [
        {
            "id": "long-clause",
            "text": prefix + clause + "\n\n结束。",
            "evidence": clause,
            "questions": [("白鹭专项费用不超过多少元时，由谁批准？", ["128", "部门负责人"])],
        },
        {
            "id": "table",
            "text": table_prefix + table + "\n\n咨询客服。",
            "evidence": table.strip(),
            "questions": [("标准套餐容量是多少，保留期多少天？", ["20", "30"])],
        },
        {
            "id": "policy",
            "text": policy,
            "evidence": "白鹭验收计划员工午餐报销上限为每人每天 128 元。必须提交电子发票。",
            "questions": [
                ("白鹭验收计划午餐报销每天上限多少元？", ["128"]),
                ("白鹭验收计划报销必须提交什么凭证？", ["电子发票"]),
                ("白鹭验收计划员工午餐报销必须提交什么凭证？", ["电子发票"]),
                ("白鹭验收计划年终奖金是多少？", None),
            ],
        },
    ]


def counts():
    with SessionLocal() as db:
        return {
            t.name: db.scalar(select(func.count()).select_from(t))
            for t in Base.metadata.sorted_tables
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixed-url", default="http://127.0.0.1:8011/api/v1")
    parser.add_argument("--structure-url", default="http://127.0.0.1:8012/api/v1")
    parser.add_argument("--output", default=str(ROOT / "evals/chunking/results.json"))
    options = parser.parse_args()
    cases = dataset()
    settings = get_settings()
    report = {
        "kind": "paired synthetic development comparison; not blind",
        "metadata": {
            "llm_model": settings.llm_model,
            "embedding_model": settings.embedding_model,
            "embedding_max_length": settings.embedding_max_length,
            "top_k": 3,
            "size": 800,
            "overlap": 100,
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "working_tree_dirty": bool(
                subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
            ),
            "dataset_sha256": hashlib.sha256(
                json.dumps(cases, ensure_ascii=False).encode()
            ).hexdigest(),
        },
        "cases": cases,
        "rows": [],
    }
    store, storage = MilvusStore(), LocalStorage(ROOT)
    before, files_before = counts(), set(storage.directory.iterdir())
    vectors_before = store.client.query(store.name, filter="", output_fields=["count(*)"])[0]
    tenant_id, user_id = None, None
    kbs = []
    token = secrets.token_urlsafe(32)
    headers = {"Authorization": "Bearer " + token}
    clients = {
        name: httpx.Client(base_url=url, headers=headers, timeout=180)
        for name, url in (("fixed", options.fixed_url), ("structure", options.structure_url))
    }

    def request(client, method, path, expected=200, **kwargs):
        r = client.request(method, path, **kwargs)
        assert r.status_code == expected, f"{method} {path}: {r.status_code}"
        return r.json()

    try:
        for url in (options.fixed_url, options.structure_url):
            assert httpx.get(url.rstrip("/") + "/knowledge-bases", timeout=10).status_code == 401, (
                "Comparison APIs must enforce authentication"
            )
        marker = "chunking-" + uuid4().hex[:12]
        with SessionLocal.begin() as db:
            tenant = Tenant(name=marker, slug=marker)
            db.add(tenant)
            db.flush()
            tenant_id = tenant.id
            user = User(email=marker + "@example.invalid", role="admin", tenant_id=tenant_id)
            db.add(user)
            db.flush()
            user_id = user.id
            db.add(ApiToken(user_id=user_id, token_hash=hash_token(token)))
        with tempfile.TemporaryDirectory() as temp:
            for strategy, client in clients.items():
                for case in cases:
                    path = Path(temp) / (case["id"] + ".md")
                    path.write_text(case["text"])
                    chunks = parse_chunks(path, strategy=strategy)
                    evidence_whole = any(case["evidence"] in c["content"] for c in chunks)
                    kb = request(
                        client,
                        "POST",
                        "/knowledge-bases",
                        201,
                        json={"name": marker + "-" + strategy + "-" + case["id"]},
                    )
                    kbs.append((client, kb["id"], kb["name"]))
                    doc = request(
                        client,
                        "POST",
                        f"/knowledge-bases/{kb['id']}/documents",
                        202,
                        files={"file": (path.name, case["text"].encode())},
                    )
                    for _ in range(300):
                        with SessionLocal() as db:
                            v = db.get(DocumentVersion, doc["version_id"])
                            assert v.chunk_strategy == strategy, "API policy snapshot differs"
                            job = db.scalar(
                                select(VectorIndex).where(
                                    VectorIndex.version_id == v.id,
                                    VectorIndex.collection == store.name,
                                )
                            )
                            assert v.status != "failed" and not (job and job.status == "failed")
                            if job and job.status == "indexed":
                                actual = list(
                                    db.scalars(
                                        select(Chunk.content)
                                        .where(Chunk.version_id == v.id)
                                        .order_by(Chunk.position)
                                    )
                                )
                                assert actual == [c["content"] for c in chunks], (
                                    "Worker chunks differ from captured policy"
                                )
                                break
                        time.sleep(1)
                    else:
                        raise AssertionError("Index timeout")
                    for question, keywords in case["questions"]:
                        query = {"query": question, "knowledge_base_id": kb["id"], "top_k": 3}
                        retrieved = request(client, "POST", "/search", json=query)
                        start = time.perf_counter()
                        answer = request(
                            client,
                            "POST",
                            "/chat/ask",
                            json={"question": question, "knowledge_base_id": kb["id"], "top_k": 3},
                        )
                        passed = (
                            (
                                answer["answerable"]
                                and bool(answer["citations"])
                                and all(k in answer["answer"] for k in keywords)
                            )
                            if keywords
                            else not answer["answerable"]
                        )
                        report["rows"].append(
                            {
                                "strategy": strategy,
                                "case": case["id"],
                                "question": question,
                                "chunk_count": len(chunks),
                                "max_chunk_chars": max(len(c["content"]) for c in chunks),
                                "evidence_whole_in_any_chunk": evidence_whole,
                                "evidence_whole_in_retrieved_chunk": any(
                                    case["evidence"] in h["content"] for h in retrieved["hits"]
                                ),
                                "heuristic_passed": bool(passed),
                                "http_ms": round((time.perf_counter() - start) * 1000, 2),
                                "retrieved_hits": retrieved["hits"],
                                "response": answer,
                            }
                        )
                        print(
                            strategy,
                            case["id"],
                            "question",
                            len(report["rows"]),
                            "heuristic",
                            bool(passed),
                            flush=True,
                        )
        report["summary"] = {}
        for strategy in clients:
            rows = [r for r in report["rows"] if r["strategy"] == strategy]
            by_case = {r["case"]: r for r in rows}
            report["summary"][strategy] = {
                "questions": len(rows),
                "heuristic_passed": sum(r["heuristic_passed"] for r in rows),
                "documents": len(by_case),
                "whole_evidence_documents": sum(
                    r["evidence_whole_in_any_chunk"] for r in by_case.values()
                ),
                "chunks": sum(r["chunk_count"] for r in by_case.values()),
            }
    finally:
        for client, kb_id, name in kbs:
            request(client, "DELETE", f"/knowledge-bases/{kb_id}", json={"confirm_name": name})
        with SessionLocal.begin() as db:
            if tenant_id is not None:
                db.execute(delete(AuditLog).where(AuditLog.tenant_id == tenant_id))
            if user_id is not None:
                db.execute(delete(ApiToken).where(ApiToken.user_id == user_id))
                db.execute(delete(User).where(User.id == user_id))
            if tenant_id is not None:
                db.execute(delete(Tenant).where(Tenant.id == tenant_id))
        report["baseline_restored"] = (
            counts() == before
            and set(storage.directory.iterdir()) == files_before
            and store.client.query(store.name, filter="", output_fields=["count(*)"])[0]
            == vectors_before
        )
        target = Path(options.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        for client in clients.values():
            client.close()
        store.close()
        assert report["baseline_restored"], "Fixture baseline mismatch"
    print(json.dumps(report["summary"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
