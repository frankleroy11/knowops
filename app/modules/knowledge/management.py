"""Administrator deletion: serialize writers, reject active jobs, then clean external data."""

import logging

from fastapi import HTTPException
from sqlalchemy import delete, select

from app.adapters.storage import LocalStorage
from app.adapters.vectorstore.milvus import MilvusStore, collection_name
from app.modules.audit import service as audit
from app.modules.auth.models import KbMember
from app.modules.feedback.models import AnswerFeedback
from app.modules.knowledge.models import (
    Chunk,
    Document,
    DocumentVersion,
    KnowledgeBase,
    VectorIndex,
)


def delete_knowledge_base(db, principal, kb_id, confirmation, storage: LocalStorage):
    from app.modules.auth import service

    # Check tenant visibility before asking for destructive privilege.
    kb = service.require_kb(db, principal, kb_id, "read")
    service.require_admin(principal)
    kb = db.scalar(
        select(KnowledgeBase)
        .where(KnowledgeBase.id == kb_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if kb is None:
        raise HTTPException(404, "知识库不存在")
    if confirmation != kb.name:
        raise HTTPException(409, "知识库名称不匹配，请刷新后重新确认")
    documents = list(db.scalars(select(Document.id).where(Document.knowledge_base_id == kb_id)))
    versions = list(
        db.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.document_id.in_(documents))
            .order_by(DocumentVersion.id)
            .with_for_update()
        )
    )
    version_ids = [v.id for v in versions]
    jobs = list(
        db.scalars(
            select(VectorIndex).where(VectorIndex.version_id.in_(version_ids)).with_for_update()
        )
    )
    if any(v.status == "pending" for v in versions) or any(j.status == "indexing" for j in jobs):
        raise HTTPException(409, "文档正在解析或索引，请等待任务完成后再删除")
    paths = {v.storage_path for v in versions}
    # Validate paths BEFORE any irreversible external operation.
    for path in paths:
        storage.checked_delete_path(path)
    chunks = list(db.scalars(select(Chunk.id).where(Chunk.version_id.in_(version_ids))))
    collections = {collection_name(), *(j.collection for j in jobs)}
    store = None
    try:
        store = MilvusStore()
        for collection in sorted(collections):
            store.delete_knowledge_base(kb_id, collection)
    except Exception:  # noqa: BLE001 - never expose provider details
        db.rollback()
        logging.getLogger(__name__).warning("Knowledge-base vector cleanup failed for %s", kb_id)
        raise HTTPException(
            503, "向量清理未完成，知识库及文件仍保留，请重试删除；部分向量可能已清理"
        ) from None
    finally:
        if store:
            try:
                store.close()
            except Exception:  # noqa: BLE001 - closure must not mask cleanup result
                logging.getLogger(__name__).warning("Vector client close failed")
    tenant_id, name = kb.tenant_id, kb.name
    counts = {"documents": len(documents), "versions": len(versions), "chunks": len(chunks)}
    try:
        # Audit history survives; feedback may contain references to deleted documents.
        db.execute(delete(AnswerFeedback).where(AnswerFeedback.knowledge_base_id == kb_id))
        db.execute(delete(KbMember).where(KbMember.kb_id == kb_id))
        db.execute(delete(VectorIndex).where(VectorIndex.version_id.in_(version_ids)))
        db.execute(delete(Chunk).where(Chunk.version_id.in_(version_ids)))
        db.execute(delete(DocumentVersion).where(DocumentVersion.id.in_(version_ids)))
        db.execute(delete(Document).where(Document.knowledge_base_id == kb_id))
        db.delete(kb)
        # record commits this business transaction and its audit entry together.
        audit.record(
            db,
            principal,
            "kb.delete",
            "knowledge_base",
            kb_id,
            f"name={name} documents={len(documents)} versions={len(versions)} chunks={len(chunks)}",
            tenant_id=tenant_id,
        )
    except Exception:  # noqa: BLE001 - external deletion cannot be rolled back
        db.rollback()
        raise HTTPException(503, "数据库删除未完成；向量可能已清理，请重试删除") from None
    shared = set(
        db.scalars(
            select(DocumentVersion.storage_path).where(DocumentVersion.storage_path.in_(paths))
        )
    )
    pending = 0
    for path in paths - shared:
        try:
            storage.delete(path)
        except OSError:
            pending += 1
    return {"id": kb_id, "deleted": True, **counts, "file_cleanup_pending": pending}
