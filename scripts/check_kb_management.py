"""Live, disposable KB lifecycle check; run only against a development instance.

Uses real MySQL, Milvus, storage and bearer authentication through TestClient.
Seeds a parsed/indexed fixture (does not test embedding or Celery ingestion).
Only rows and files created by this run are removed. No credentials are printed.
"""

import secrets
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.adapters.storage import LocalStorage
from app.adapters.vectorstore.milvus import MilvusStore
from app.core.config import ROOT, get_settings
from app.db.session import Base, SessionLocal
from app.main import app
from app.modules.audit.models import AuditLog
from app.modules.auth.models import ApiToken, KbMember, User
from app.modules.auth.security import hash_token
from app.modules.feedback.models import AnswerFeedback
from app.modules.knowledge.models import (
    Chunk,
    Document,
    DocumentVersion,
    KnowledgeBase,
    VectorIndex,
)
from app.modules.tenant.models import Tenant


def counts():
    with SessionLocal() as db:
        return {
            t.name: db.scalar(select(func.count()).select_from(t))
            for t in Base.metadata.sorted_tables
        }


def main():
    marker = "kb-check-" + uuid4().hex
    storage = LocalStorage(ROOT)
    store = MilvusStore()
    before = counts()
    files_before = set(storage.directory.iterdir())
    vector_before = store.client.query(store.name, filter="", output_fields=["count(*)"])[0]
    tenant_ids, user_ids, kb_id, version_id = [], [], None, None
    path = marker + ".txt"
    settings = get_settings()
    original_auth = settings.auth_mode
    settings.auth_mode = "enforced"
    try:
        tokens = []
        with SessionLocal.begin() as db:
            for i in range(2):
                tenant = Tenant(name=f"{marker}-{i}", slug=f"{marker}-{i}")
                db.add(tenant)
                db.flush()
                tenant_ids.append(tenant.id)
            for i, role in enumerate(["admin", "viewer", "admin"]):
                user = User(
                    email=f"{marker}-{i}@example.invalid", role=role, tenant_id=tenant_ids[i == 2]
                )
                db.add(user)
                db.flush()
                user_ids.append(user.id)
                token = secrets.token_urlsafe(32)
                tokens.append({"Authorization": "Bearer " + token})
                db.add(ApiToken(user_id=user.id, token_hash=hash_token(token)))
        client = TestClient(app)
        base = "/api/v1/knowledge-bases"
        response = client.post(base, json={"name": marker}, headers=tokens[0])
        assert response.status_code == 201, response.text
        kb_id = response.json()["id"]
        with SessionLocal.begin() as db:
            doc = Document(knowledge_base_id=kb_id, filename="fixture.txt")
            db.add(doc)
            db.flush()
            version = DocumentVersion(
                document_id=doc.id, content_hash="a" * 64, storage_path=path, status="parsed"
            )
            db.add(version)
            db.flush()
            version_id = version.id
            chunk = Chunk(
                version_id=version.id, position=0, content="Disposable integration fixture"
            )
            db.add(chunk)
            db.flush()
            chunk_id, doc_id = chunk.id, doc.id
            db.add(
                VectorIndex(
                    version_id=version.id, collection=store.name, status="indexed", chunks_indexed=1
                )
            )
            db.add(KbMember(kb_id=kb_id, user_id=user_ids[1], role="viewer"))
            db.add(
                AnswerFeedback(
                    knowledge_base_id=kb_id,
                    tenant_id=tenant_ids[0],
                    question="fixture",
                    rating="helpful",
                )
            )
        storage.path(path).write_text("Disposable integration fixture")
        store.upsert(
            [
                {
                    "chunk_id": chunk_id,
                    "knowledge_base_id": kb_id,
                    "document_id": doc_id,
                    "version_id": version_id,
                    "vector": [1.0] + [0.0] * (settings.embedding_dim - 1),
                }
            ]
        )
        expression = f"knowledge_base_id == {kb_id}"
        assert store.client.query(store.name, filter=expression, output_fields=["chunk_id"])
        url = f"{base}/{kb_id}"
        assert (
            client.patch(url, json={"name": marker + "-new"}, headers=tokens[1]).status_code == 403
        )
        assert (
            client.request(
                "DELETE", url, json={"confirm_name": marker}, headers=tokens[2]
            ).status_code
            == 404
        )
        assert client.request("DELETE", url, json={"confirm_name": marker}).status_code == 401
        assert (
            client.patch(url, json={"name": marker + "-new"}, headers=tokens[0]).status_code == 200
        )
        assert (
            client.request(
                "DELETE", url, json={"confirm_name": marker}, headers=tokens[0]
            ).status_code
            == 409
        )
        with SessionLocal.begin() as db:
            job = db.scalar(select(VectorIndex).where(VectorIndex.version_id == version_id))
            job.status = "indexing"
        assert (
            client.request(
                "DELETE", url, json={"confirm_name": marker + "-new"}, headers=tokens[0]
            ).status_code
            == 409
        )
        with SessionLocal.begin() as db:
            db.scalar(
                select(VectorIndex).where(VectorIndex.version_id == version_id)
            ).status = "indexed"
        response = client.request(
            "DELETE", url, json={"confirm_name": marker + "-new"}, headers=tokens[0]
        )
        assert response.status_code == 200, response.text
        assert response.json()["chunks"] == 1 and response.json()["file_cleanup_pending"] == 0
        assert not storage.path(path).exists()
        assert not store.client.query(store.name, filter=expression, output_fields=["chunk_id"])
        with SessionLocal() as db:
            assert db.get(KnowledgeBase, kb_id) is None
            assert db.get(Document, doc_id) is None
            assert db.get(DocumentVersion, version_id) is None
            assert db.get(Chunk, chunk_id) is None
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(AuditLog)
                    .where(AuditLog.tenant_id == tenant_ids[0], AuditLog.action == "kb.delete")
                )
                == 1
            )
        print(
            "PASS: real bearer ACL, rename, stale confirmation, busy guard, SQL/vector/file deletion, retained audit"
        )
    finally:
        settings.auth_mode = original_auth
        # Restrict cleanup to generated identifiers, even after a failed assertion.
        if kb_id is not None:
            store.delete_knowledge_base(kb_id)
        with SessionLocal.begin() as db:
            if kb_id is not None:
                docs = select(Document.id).where(Document.knowledge_base_id == kb_id)
                versions = select(DocumentVersion.id).where(DocumentVersion.document_id.in_(docs))
                db.execute(delete(AnswerFeedback).where(AnswerFeedback.knowledge_base_id == kb_id))
                db.execute(delete(KbMember).where(KbMember.kb_id == kb_id))
                db.execute(delete(VectorIndex).where(VectorIndex.version_id.in_(versions)))
                db.execute(delete(Chunk).where(Chunk.version_id.in_(versions)))
                db.execute(delete(DocumentVersion).where(DocumentVersion.document_id.in_(docs)))
                db.execute(delete(Document).where(Document.knowledge_base_id == kb_id))
                db.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kb_id))
            db.execute(delete(AuditLog).where(AuditLog.tenant_id.in_(tenant_ids)))
            db.execute(delete(ApiToken).where(ApiToken.user_id.in_(user_ids)))
            db.execute(delete(User).where(User.id.in_(user_ids)))
            db.execute(delete(Tenant).where(Tenant.id.in_(tenant_ids)))
        storage.delete(path)
        assert counts() == before, "Database baseline changed"
        assert set(storage.directory.iterdir()) == files_before, "Storage baseline changed"
        assert (
            store.client.query(store.name, filter="", output_fields=["count(*)"])[0]
            == vector_before
        )
        store.close()
        print("PASS: all table counts, logical vector count and storage file set restored")


if __name__ == "__main__":
    main()
