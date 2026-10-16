"""把命名为测试／评估的在线知识库替换为业务目录。

默认只预览；--apply 要求有效的本地备份，先入库并验证新资料，再按快照 ID 删除旧库。
只读取已有合成语料和平台帮助文件，不删除评测源文件或其他租户的数据。
"""

import argparse
import hashlib
import json
import time
from pathlib import Path

import httpx
from sqlalchemy import select

from app.core.config import ROOT
from app.db.session import SessionLocal
from app.modules.auth.models import User
from app.modules.knowledge.models import Chunk, KnowledgeBase

CATALOG = ROOT / "knowledge_library/catalog.json"
STATE = ROOT / ".tmp/business-library-refresh.json"
PREFIXES = ("入库验证-", "界面验收-", "页面操作验收", "评估-")


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def persist(data):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    STATE.chmod(0o600)


def seed_faqs(call, state):
    """只从新版平台帮助原文建立 FAQ，不把历史测试答案搬入新库。"""
    definitions = json.loads((ROOT / "knowledge_library/faqs.json").read_text())
    state.setdefault("faqs", {})
    for item in definitions:
        if item["question"] in state["faqs"]:
            continue
        version_id = state["uploads"][item["source"]]["version_id"]
        with SessionLocal() as db:
            chunks = list(db.scalars(select(Chunk).where(Chunk.version_id == version_id)))
            chunk = next(c for c in chunks if item["quote"] in c.content)
            chunk_id = chunk.id
        faq = call(
            "POST",
            "/admin/faqs",
            201,
            json={
                "knowledge_base_id": state["new"][item["knowledge_base"]],
                "chunk_id": chunk_id,
                "question": item["question"],
                "answer": item["answer"],
                "quote": item["quote"],
                "enabled": True,
            },
        )
        state["faqs"][item["question"]] = faq["id"]
        persist(state)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:8011/api/v1")
    args = parser.parse_args()
    catalog = json.loads(CATALOG.read_text())
    with SessionLocal() as db:
        old = [
            {"id": kb.id, "name": kb.name}
            for kb in db.scalars(
                select(KnowledgeBase).where(KnowledgeBase.tenant_id == 1).order_by(KnowledgeBase.id)
            )
            if kb.name.startswith(PREFIXES)
        ]
    print(
        "Replacement catalog:", {item["name"]: len(item["files"]) for item in catalog}, flush=True
    )
    print("Old test IDs:", [item["id"] for item in old], flush=True)
    if not args.apply:
        return
    assert args.backup, "--backup required"
    backup = json.loads((args.backup / "manifest.json").read_text())
    for name, expected in backup["sha256"].items():
        assert checksum(args.backup / name) == expected, "Backup checksum mismatch"
    assert "milvus-vectors.json" in backup["sha256"], "Vector export required"
    state = (
        json.loads(STATE.read_text())
        if STATE.exists()
        else {"old": old, "new": {}, "uploads": {}, "deleted": [], "probes": []}
    )
    if state.get("completed"):
        print("Already completed; no modifications")
        return
    state["backup"] = str(args.backup.resolve())
    creds = json.loads((ROOT / ".tmp/local-admin-credentials.json").read_text())
    client = httpx.Client(base_url=args.base_url, timeout=180)
    token = None

    def call(method, path, expected=200, **kwargs):
        response = client.request(
            method, path, headers={"Authorization": "Bearer " + token} if token else {}, **kwargs
        )
        assert response.status_code == expected, f"{method} {path}: HTTP {response.status_code}"
        return response.json() if response.content else None

    try:
        token = call("POST", "/auth/password/login", json=creds)["token"]
        me = call("GET", "/auth/me")
        assert me["is_admin"] and me["tenant_id"] == 1
        persist(state)
        for item in catalog:
            name = item["name"]
            if name not in state["new"]:
                kb = call(
                    "POST",
                    "/knowledge-bases",
                    201,
                    json={"name": name, "description": item["description"]},
                )
                state["new"][name] = kb["id"]
                persist(state)
            kb_id = state["new"][name]
            for source in item["files"]:
                path = ROOT / source
                assert path.is_file()
                if source in state["uploads"]:
                    assert state["uploads"][source]["sha256"] == checksum(path), (
                        "Source changed during refresh"
                    )
                    continue
                result = call(
                    "POST",
                    f"/knowledge-bases/{kb_id}/documents",
                    202,
                    files={"file": (path.name, path.read_bytes())},
                )
                assert result["queued"], "Queue rejected; old KBs preserved"
                state["uploads"][source] = {
                    **result,
                    "sha256": checksum(path),
                    "knowledge_base_id": kb_id,
                }
                persist(state)
            print("Uploaded:", name, len(item["files"]), flush=True)
        # 任何一个新文档失败都不删除旧库；保存状态以便定位和恢复。
        deadline = time.monotonic() + 1200
        while time.monotonic() < deadline:
            docs = []
            for kb_id in state["new"].values():
                docs += call("GET", f"/knowledge-bases/{kb_id}/documents?limit=100")
            failed = [d for d in docs if d["status"] == "failed" or d["index_status"] == "failed"]
            if failed:
                state["failures"] = failed
                persist(state)
                raise RuntimeError("New-document failures: old knowledge bases preserved")
            ready = sum(d["status"] == "parsed" and d["index_status"] == "indexed" for d in docs)
            print("Index progress:", ready, "/", len(state["uploads"]), flush=True)
            if ready == len(state["uploads"]) and len(docs) == len(state["uploads"]):
                break
            time.sleep(5)
        else:
            raise RuntimeError("Index timeout; old knowledge bases preserved")
        # 每个新库执行一次真实 BGE-M3 / Milvus 检索，确认可返回本库原文。
        for item in catalog:
            kb_id = state["new"][item["name"]]
            query = Path(item["files"][0]).stem
            result = call(
                "POST", "/search", json={"query": query, "knowledge_base_id": kb_id, "top_k": 3}
            )
            assert result["hits"] and all(
                hit["knowledge_base_id"] == kb_id for hit in result["hits"]
            )
            state["probes"].append(
                {"knowledge_base": item["name"], "query": query, "hit_count": len(result["hits"])}
            )
        persist(state)
        # 保留现有普通用户；只在其本租户增加新库成员关系。
        with SessionLocal() as db:
            users = [
                (u.email, u.role)
                for u in db.scalars(
                    select(User).where(
                        User.tenant_id == 1, User.is_active.is_(True), User.role != "admin"
                    )
                )
            ]
        for kb_id in state["new"].values():
            for email, role in users:
                call(
                    "POST",
                    f"/knowledge-bases/{kb_id}/members",
                    201,
                    json={"email": email, "role": "editor" if role == "editor" else "viewer"},
                )
        seed_faqs(call, state)
        # 新目录已经验证，才删除本次快照中的测试库。名称变更或不在范围内则停止。
        for item in state["old"]:
            if item["id"] in state["deleted"]:
                continue
            with SessionLocal() as db:
                kb = db.get(KnowledgeBase, item["id"])
                if kb is None:
                    state["deleted"].append(item["id"])
                    persist(state)
                    continue
                assert (
                    kb.tenant_id == 1 and kb.name == item["name"] and kb.name.startswith(PREFIXES)
                )
            result = call(
                "DELETE", f"/knowledge-bases/{item['id']}", json={"confirm_name": item["name"]}
            )
            assert result["file_cleanup_pending"] == 0
            state["deleted"].append(item["id"])
            persist(state)
            print("Removed old test KB:", item["id"], item["name"], flush=True)
        state["completed"] = True
        persist(state)
        print("PASS: business libraries ready, old test libraries removed", flush=True)
    finally:
        if token:
            call("POST", "/auth/logout")
        client.close()


if __name__ == "__main__":
    main()
