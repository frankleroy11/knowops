"""真实 FAQ / Redis / RAG 验收；使用合成临时资料，会调用 Qwen，结束后按精确 ID 清理。"""

import argparse
import json
import secrets
import time
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.modules.audit.models import AuditLog
from app.modules.auth.models import ApiToken, KbMember, LoginAttempt, User
from app.modules.auth.security import hash_password
from app.modules.faq.cache import client as redis_client
from app.modules.faq.models import Faq
from app.modules.knowledge.models import Chunk, DocumentVersion
from app.modules.tenant.models import Tenant


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8010/api/v1")
    parser.add_argument("--report", default=".tmp/faq-cache-acceptance.json")
    args = parser.parse_args()
    marker = "faq-acceptance-" + uuid4().hex[:12]
    password = "Demo9!" + secrets.token_hex(12)
    user_ids, tenant_id, kb_id, faq_id = [], None, None, None
    report = {"kind": "synthetic development acceptance", "checks": [], "responses": {}}
    client = httpx.Client(base_url=args.base_url, timeout=180)
    token = None
    viewer = None

    def call(method, path, expected=200, auth=None, **kwargs):
        response = client.request(
            method,
            path,
            headers={"Authorization": "Bearer " + (auth or token)} if (auth or token) else {},
            **kwargs,
        )
        assert response.status_code == expected, f"{method} {path}: {response.status_code}"
        return response.json() if response.content else None

    try:
        with SessionLocal.begin() as db:
            tenant = Tenant(name=marker, slug=marker)
            db.add(tenant)
            db.flush()
            tenant_id = tenant.id
            for role in ["admin", "viewer"]:
                user = User(
                    email=f"{role}-{marker}@example.invalid",
                    role=role,
                    tenant_id=tenant_id,
                    password_hash=hash_password(password),
                )
                db.add(user)
                db.flush()
                user_ids.append(user.id)
        token = call(
            "POST",
            "/auth/password/login",
            json={"email": f"admin-{marker}@example.invalid", "password": password},
        )["token"]
        viewer = call(
            "POST",
            "/auth/password/login",
            json={"email": f"viewer-{marker}@example.invalid", "password": password},
        )["token"]
        kb = call("POST", "/knowledge-bases", 201, json={"name": marker})
        kb_id = kb["id"]
        call(
            "POST",
            f"/knowledge-bases/{kb_id}/members",
            201,
            json={"email": f"viewer-{marker}@example.invalid", "role": "viewer"},
        )
        upload = call(
            "POST",
            f"/knowledge-bases/{kb_id}/documents",
            202,
            files={
                "file": (
                    "FAQ验收制度.txt",
                    "白鹭 FAQ 验收计划的午餐报销上限为每人每天 128 元，必须提交电子发票。".encode(),
                )
            },
        )
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            state = call("GET", f"/document-versions/{upload['version_id']}/index")
            if state["status"] == "indexed":
                break
            assert state["status"] != "failed", "Index failed"
            time.sleep(1)
        else:
            raise AssertionError("Index timeout")
        with SessionLocal() as db:
            chunk = db.scalar(select(Chunk).where(Chunk.version_id == upload["version_id"]))
            chunk_id = chunk.id
        question = "白鹭 FAQ 验收计划的午餐报销每天上限是多少？"
        body = {
            "knowledge_base_id": kb_id,
            "chunk_id": chunk_id,
            "question": question,
            "answer": "每人每天最多报销 128 元。",
            "quote": "午餐报销上限为每人每天 128 元",
            "enabled": True,
        }
        faq = call("POST", "/admin/faqs", 201, json=body)
        faq_id = faq["id"]
        assert call("GET", f"/admin/faqs?knowledge_base_id={kb_id}")[0]["source_valid"]
        result = call("POST", "/chat/ask", auth=viewer, json={"question": question, "scope": "all"})
        assert result["answer_source"] == "faq" and result["faq_match"] == "exact"
        report["responses"]["exact"] = result
        semantic = call(
            "POST", "/chat/ask", auth=viewer, json={"question": question[:-1], "scope": "all"}
        )
        assert semantic["answer_source"] == "faq" and semantic["faq_match"] == "semantic"
        report["responses"]["semantic"] = semantic
        report["checks"].append("real_upload_index_faq_exact_and_semantic_without_llm")
        body["enabled"] = False
        call("PUT", f"/admin/faqs/{faq_id}", json=body)
        ask = {"question": question, "scope": "all"}
        first = call("POST", "/chat/ask", auth=viewer, json=ask)
        assert first["answer_source"] == "rag" and first["answerable"]
        second = call("POST", "/chat/ask", auth=viewer, json=ask)
        assert second["answer_source"] == "cache" and second["answer"] == first["answer"]
        report["responses"]["rag"] = first
        report["responses"]["cache"] = second
        report["checks"].append("real_qwen_first_answer_then_redis_cache_hit")
        # 移除用户成员关系后不能读到刚才的缓存；随后恢复该临时成员。
        call("DELETE", f"/knowledge-bases/{kb_id}/members/{user_ids[1]}", 204)
        denied = call("POST", "/chat/ask", auth=viewer, json=ask)
        assert denied["answer_source"] != "cache" and not denied["answerable"]
        call(
            "POST",
            f"/knowledge-bases/{kb_id}/members",
            201,
            json={"email": f"viewer-{marker}@example.invalid", "role": "viewer"},
        )
        report["checks"].append("permission_revocation_blocks_cached_answer")
        # 下架证据使 FAQ 和缓存同时失效，旧资料不会继续提供标准答案。
        body["enabled"] = True
        call("PUT", f"/admin/faqs/{faq_id}", json=body)
        with SessionLocal.begin() as db:
            db.get(DocumentVersion, upload["version_id"]).is_current = False
        stale = call("POST", "/chat/ask", auth=viewer, json=ask)
        assert not stale["answerable"] and stale["answer_source"] != "faq"
        report["checks"].append("version_invalidation_blocks_faq_and_cache")
        report["passed"] = True
    finally:
        if faq_id and not kb_id:
            call("DELETE", f"/admin/faqs/{faq_id}", 204)
        if kb_id:
            call("DELETE", f"/knowledge-bases/{kb_id}", json={"confirm_name": marker})
        with SessionLocal.begin() as db:
            if faq_id:
                assert db.get(Faq, faq_id) is None, "FAQ cascade cleanup failed"
            db.execute(delete(Faq).where(Faq.knowledge_base_id == kb_id))
            db.execute(delete(KbMember).where(KbMember.user_id.in_(user_ids)))
            db.execute(delete(AuditLog).where(AuditLog.actor_id.in_(user_ids)))
            if tenant_id is not None:
                db.execute(delete(AuditLog).where(AuditLog.tenant_id == tenant_id))
            db.execute(delete(ApiToken).where(ApiToken.user_id.in_(user_ids)))
            db.execute(
                delete(LoginAttempt).where(
                    LoginAttempt.email.in_(
                        [f"admin-{marker}@example.invalid", f"viewer-{marker}@example.invalid"]
                    )
                )
            )
            db.execute(delete(User).where(User.id.in_(user_ids)))
            if tenant_id:
                db.execute(delete(Tenant).where(Tenant.id == tenant_id))
        # 只清理这次临时用户的缓存：由响应无法获得 key，因此让短 TTL 自然失效。
        # 不执行 FLUSHDB，不影响 Celery 队列或其他用户缓存。
        with redis_client() as redis:
            assert redis.ping()
        client.close()
        report["temporary_rows_cleaned"] = True
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print("PASS", len(report["checks"]), "real FAQ/cache checks; report:", args.report)


if __name__ == "__main__":
    main()
