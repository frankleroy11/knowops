# 中文导读：
# 真实认证、上传、审核、索引、问答和清理验收，依赖 Worker 与模型服务
# 使用临时数据并核对清理后的基线

"""Disposable live release regression against an AUTH_MODE=enforced development API.

Runs real password login, ACL, upload/Celery/BGE-M3/Milvus, review, version
switching, Qwen, citations, feedback and document deletion. Synthetic development
checks, not a blind or production evaluation. Raw credentials never leave memory.
"""

import argparse
import json
import secrets
import time
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import delete, func, select

from app.adapters.storage import LocalStorage
from app.adapters.vectorstore.milvus import MilvusStore
from app.core.config import ROOT
from app.db.session import Base, SessionLocal
from app.main import app  # noqa: F401 - register all mapped tables
from app.modules.audit.models import AuditLog
from app.modules.auth.models import ApiToken, LoginAttempt, PasswordHistory, User
from app.modules.auth.security import hash_password
from app.modules.feedback.models import AnswerFeedback
from app.modules.knowledge.models import DocumentVersion, KnowledgeBase, VectorIndex
from app.modules.tenant.models import Tenant


def counts():
    with SessionLocal() as db:
        return {
            t.name: db.scalar(select(func.count()).select_from(t))
            for t in Base.metadata.sorted_tables
        }


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--base-url", default="http://127.0.0.1:8011/api/v1")
    args.add_argument("--report", default=str(ROOT / ".tmp/release-regression.json"))
    options = args.parse_args()
    marker = "release-" + uuid4().hex[:12]
    storage, store = LocalStorage(ROOT), MilvusStore()
    before, files_before = counts(), set(storage.directory.iterdir())
    before_vectors = store.client.query(store.name, filter="", output_fields=["count(*)"])[0]
    tenant_ids, user_ids, kb_ids, paths, checks, rows = [], [], [], set(), [], []
    client = httpx.Client(base_url=options.base_url, timeout=180)
    report = {
        "run": marker,
        "kind": "synthetic development regression",
        "checks": checks,
        "questions": rows,
    }

    def request(method, path, token=None, expected=200, **kwargs):
        headers = {"Authorization": "Bearer " + token} if token else {}
        response = client.request(method, path, headers=headers, **kwargs)
        assert response.status_code == expected, f"{method} {path}: HTTP {response.status_code}"
        return response.json() if response.content else None

    def wait(version_id, expected="indexed"):
        started = time.monotonic()
        while time.monotonic() - started < 300:
            with SessionLocal() as db:
                v = db.get(DocumentVersion, version_id)
                if v:
                    paths.add(v.storage_path)
                job = db.scalar(
                    select(VectorIndex).where(
                        VectorIndex.version_id == version_id, VectorIndex.collection == store.name
                    )
                )
                if expected == "failed" and v.status == "failed":
                    return
                if v.status == "failed" or (job and job.status == "failed"):
                    raise AssertionError("Fixture processing failed")
                if job and job.status == "indexed":
                    return
            time.sleep(1)
        raise AssertionError("Worker processing timeout")

    try:
        assert client.get("/knowledge-bases").status_code == 401
        credentials = {}
        with SessionLocal.begin() as db:
            # Password login clears failures for the request IP; do not run when
            # unrelated failures exist, so this regression cannot erase them.
            assert db.scalar(select(func.count()).select_from(LoginAttempt)) == 0
            for i in range(2):
                tenant = Tenant(name=f"{marker}-{i}", slug=f"{marker}-{i}")
                db.add(tenant)
                db.flush()
                tenant_ids.append(tenant.id)
            for label, role, tenant_id in [
                ("platform", "admin", None),
                ("admin", "admin", tenant_ids[0]),
                ("editor", "editor", tenant_ids[0]),
                ("viewer", "viewer", tenant_ids[0]),
                ("outsider", "admin", tenant_ids[1]),
            ]:
                password = "Aa1!" + secrets.token_hex(16)
                email = f"{label}-{marker}@example.invalid"
                user = User(
                    email=email,
                    role=role,
                    tenant_id=tenant_id,
                    password_hash=hash_password(password),
                )
                db.add(user)
                db.flush()
                user_ids.append(user.id)
                credentials[label] = (email, password)
        tokens = {}
        for role, (email, password) in credentials.items():
            tokens[role] = request(
                "POST", "/auth/password/login", json={"email": email, "password": password}
            )["token"]
        checks.append("real_password_login_all_roles")
        admin, editor, viewer = (tokens[k] for k in ("admin", "editor", "viewer"))
        kb = request(
            "POST", "/knowledge-bases", admin, 201, json={"name": marker, "review_required": True}
        )
        kb_ids.append(kb["id"])
        for role, member_role in [("editor", "editor"), ("viewer", "viewer")]:
            request(
                "POST",
                f"/knowledge-bases/{kb['id']}/members",
                admin,
                201,
                json={"email": credentials[role][0], "role": member_role},
            )
        url = f"/knowledge-bases/{kb['id']}/documents"
        request("POST", url, viewer, 403, files={"file": ("denied.txt", b"no")})
        request("GET", url, tokens["outsider"], 404)
        request("GET", "/admin/users", viewer, 403)
        request("GET", "/admin/system/status", admin, 403)
        request("GET", "/admin/system/status", tokens["platform"])
        assert len(request("GET", "/knowledge-bases", viewer)) == 1
        checks.append("platform_tenant_editor_viewer_and_cross_tenant_acl")
        policy = "白鹭验收计划员工午餐报销上限为每人每天 100 元。必须提交电子发票。"
        first = request("POST", url, editor, 202, files={"file": ("午餐制度.txt", policy.encode())})
        wait(first["version_id"])
        hits = request(
            "POST", "/search", viewer, json={"query": "白鹭验收计划午餐报销上限", "scope": "all"}
        )
        assert not hits["hits"], "Unreviewed upload leaked"
        request(
            "POST",
            f"/document-versions/{first['version_id']}/review",
            editor,
            409,
            json={"decision": "approve"},
        )
        request(
            "POST",
            f"/document-versions/{first['version_id']}/review",
            admin,
            json={"decision": "approve"},
        )
        second = request(
            "POST",
            f"/documents/{first['document_id']}/versions",
            editor,
            202,
            files={"file": ("午餐制度.txt", policy.replace("100", "128").encode())},
        )
        wait(second["version_id"])
        request("POST", f"/document-versions/{second['version_id']}/publish", editor, 409)
        request(
            "POST",
            f"/document-versions/{second['version_id']}/review",
            admin,
            json={"decision": "approve"},
        )
        request("POST", f"/document-versions/{first['version_id']}/publish", editor)
        request("POST", f"/document-versions/{second['version_id']}/publish", editor)
        assert len(request("GET", f"/documents/{first['document_id']}/versions", viewer)) == 2
        checks.append("real_upload_parse_embed_index_review_version_switch")
        vpn = request(
            "POST",
            url,
            editor,
            202,
            files={
                "file": (
                    "VPN说明.txt",
                    "白鹭验收计划的 VPN 服务使用 TCP 443 端口，连接时需要公司账号和动态验证码。".encode(),
                )
            },
        )
        wait(vpn["version_id"])
        request(
            "POST",
            f"/document-versions/{vpn['version_id']}/review",
            admin,
            json={"decision": "approve"},
        )
        bad = request("POST", url, editor, 202, files={"file": ("损坏文本.txt", b"\xff\xfe")})
        wait(bad["version_id"], "failed")
        failures = request("GET", "/admin/document-failures", admin)
        assert [r["version_id"] for r in failures] == [bad["version_id"]]
        request("POST", f"/document-versions/{bad['version_id']}/retry", viewer, 403)
        request("POST", f"/document-versions/{bad['version_id']}/retry", editor, 202)
        wait(bad["version_id"], "failed")
        repaired = request(
            "POST",
            f"/documents/{bad['document_id']}/versions",
            editor,
            202,
            files={"file": ("损坏文本.txt", "白鹭验收计划文档编码使用 UTF-8。".encode())},
        )
        wait(repaired["version_id"])
        request(
            "POST",
            f"/document-versions/{repaired['version_id']}/review",
            admin,
            json={"decision": "approve"},
        )
        checks.append("failure_location_acl_retry_and_repaired_new_version")
        questions = [
            ("白鹭验收计划午餐报销每天上限多少元？", "128"),
            ("白鹭验收计划报销必须提交什么凭证？", "电子发票"),
            ("白鹭验收计划 VPN 使用哪个 TCP 端口？", "443"),
            ("白鹭验收计划年终奖金是多少？", None),
            ("白鹭验收计划午餐上限和年终奖金分别是多少？", None),
        ]
        for question, keyword in questions:
            retrieved = request(
                "POST", "/search", viewer, json={"query": question, "scope": "all", "top_k": 3}
            )
            start = time.perf_counter()
            result = request(
                "POST", "/chat/ask", viewer, json={"question": question, "scope": "all", "top_k": 3}
            )
            citations = result["citations"]
            allowed = all(c["knowledge_base_id"] == kb["id"] for c in citations)
            heuristic = (
                (result["answerable"] and keyword in result["answer"] and bool(citations))
                if keyword
                else not result["answerable"]
            )
            rows.append(
                {
                    "question": question,
                    "retrieved_hits": retrieved["hits"],
                    "expected_keyword": keyword,
                    "passed_heuristic": heuristic,
                    "citations_in_scope": allowed,
                    "http_total_ms": round((time.perf_counter() - start) * 1000, 2),
                    "response": result,
                }
            )
            print("Question complete:", len(rows), "heuristic=", heuristic, flush=True)
        answer = rows[0]["response"]
        request(
            "POST",
            "/feedback",
            viewer,
            201,
            json={
                "rating": "helpful",
                "question": questions[0][0],
                "answer": answer["answer"],
                "scope": "knowledge_base",
                "knowledge_base_id": kb["id"],
                "grounding_status": answer["grounding_status"],
                "citation_count": len(answer["citations"]),
            },
        )
        checks.append("real_qwen_unified_qa_citations_and_feedback")
        request(
            "DELETE",
            f"/documents/{bad['document_id']}",
            viewer,
            403,
            json={"confirm_filename": "损坏文本.txt"},
        )
        request(
            "DELETE",
            f"/documents/{bad['document_id']}",
            admin,
            409,
            json={"confirm_filename": "wrong"},
        )
        deleted = request(
            "DELETE",
            f"/documents/{bad['document_id']}",
            admin,
            json={"confirm_filename": "损坏文本.txt"},
        )
        assert deleted["versions"] == 2 and deleted["file_cleanup_pending"] == 0
        assert not store.client.query(
            store.name, filter=f"document_id == {bad['document_id']}", output_fields=["chunk_id"]
        )
        request("GET", f"/documents/{first['document_id']}", viewer)
        checks.append("real_document_delete_all_versions_vectors_files_and_neighbor_preservation")
        report["summary"] = {
            "questions": len(rows),
            "heuristic_passed": sum(r["passed_heuristic"] for r in rows),
            "citation_scope_passed": sum(r["citations_in_scope"] for r in rows),
            "semantic_human_review": "required; exact quote validation is not semantic proof",
        }
    finally:
        # API cleanup rejects active jobs; never force-delete their locked inputs.
        for kb_id in kb_ids:
            with SessionLocal() as db:
                kb = db.get(KnowledgeBase, kb_id)
                name = kb.name if kb else None
            if name:
                response = client.request(
                    "DELETE",
                    f"/knowledge-bases/{kb_id}",
                    headers={"Authorization": "Bearer " + tokens["admin"]},
                    json={"confirm_name": name},
                )
                assert response.status_code == 200, (
                    "Fixture cleanup blocked; preserve IDs in report for retry"
                )
        with SessionLocal.begin() as db:
            db.execute(delete(AnswerFeedback).where(AnswerFeedback.user_id.in_(user_ids)))
            db.execute(delete(AuditLog).where(AuditLog.actor_id.in_(user_ids)))
            db.execute(delete(AuditLog).where(AuditLog.tenant_id.in_(tenant_ids)))
            db.execute(delete(ApiToken).where(ApiToken.user_id.in_(user_ids)))
            db.execute(delete(PasswordHistory).where(PasswordHistory.user_id.in_(user_ids)))
            db.execute(delete(User).where(User.id.in_(user_ids)))
            db.execute(delete(Tenant).where(Tenant.id.in_(tenant_ids)))
        report["baseline_restored"] = (
            counts() == before
            and set(storage.directory.iterdir()) == files_before
            and store.client.query(store.name, filter="", output_fields=["count(*)"])[0]
            == before_vectors
        )
        Path(options.report).parent.mkdir(parents=True, exist_ok=True)
        Path(options.report).write_text(json.dumps(report, ensure_ascii=False, indent=2))
        store.close()
        client.close()
        assert report["baseline_restored"], "Baseline changed"
    print("PASS checks:", len(checks), "Report:", options.report, flush=True)


if __name__ == "__main__":
    main()
