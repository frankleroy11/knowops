"""Document lifecycle operations with KB -> version locking order."""

import logging

from fastapi import HTTPException
from sqlalchemy import delete, select

from app.adapters.vectorstore.milvus import MilvusStore, collection_name
from app.modules.audit import service as audit
from app.modules.auth import service as auth
from app.modules.knowledge.models import Chunk, Document, DocumentVersion, VectorIndex


def locked_document(db, principal, document_id, *, admin=False):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(404, "文档不存在")
    kb = auth.require_kb(db, principal, document.knowledge_base_id, "write")
    if admin:
        auth.require_admin(principal)
    document = db.scalar(
        select(Document)
        .where(Document.id == document_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if document is None:
        raise HTTPException(404, "文档不存在")
    return document, kb


def delete_document(db, principal, document_id, confirmation, storage):
    document, kb = locked_document(db, principal, document_id, admin=True)
    if confirmation != document.filename:
        raise HTTPException(409, "文件名不匹配，请刷新后重新确认")
    versions = list(
        db.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.id)
            .with_for_update()
        )
    )
    ids = [v.id for v in versions]
    indexes = list(
        db.scalars(select(VectorIndex).where(VectorIndex.version_id.in_(ids)).with_for_update())
    )
    if any(v.status == "pending" for v in versions) or any(i.status == "indexing" for i in indexes):
        raise HTTPException(409, "文档正在解析或索引，请等待后再删除")
    paths = {v.storage_path for v in versions}
    for path in paths:
        storage.checked_delete_path(path)
    count = len(list(db.scalars(select(Chunk.id).where(Chunk.version_id.in_(ids)))))
    store = None
    try:
        store = MilvusStore()
        for name in sorted({collection_name(), *(i.collection for i in indexes)}):
            store.delete_document(document_id, name)
    except Exception:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            503, "向量清理未完成，文档与文件保留；部分向量可能已清理，请重试"
        ) from None
    finally:
        if store:
            try:
                store.close()
            except Exception:  # noqa: BLE001
                logging.getLogger(__name__).warning("Vector client close failed")
    try:
        db.execute(delete(VectorIndex).where(VectorIndex.version_id.in_(ids)))
        db.execute(delete(Chunk).where(Chunk.version_id.in_(ids)))
        db.execute(delete(DocumentVersion).where(DocumentVersion.id.in_(ids)))
        db.delete(document)
        audit.record(
            db,
            principal,
            "document.delete",
            "document",
            document_id,
            f"filename={document.filename} versions={len(ids)} chunks={count}",
            tenant_id=kb.tenant_id,
        )
    except Exception:  # noqa: BLE001
        db.rollback()
        raise HTTPException(503, "数据库删除未完成；向量可能已清理，请重试") from None
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
    return {
        "id": document_id,
        "deleted": True,
        "versions": len(ids),
        "chunks": count,
        "file_cleanup_pending": pending,
    }
