"""Embed and upsert one document version.

Database transactions are deliberately short: inputs are snapshotted first and results
are written last, so a slow embedding (model load, MPS, blocked network) never holds
row locks on `document_versions`. Holding `SELECT ... FOR UPDATE` across the embedding
call previously blocked review/publish writes for minutes on the same document.

Duplicate deliveries may embed twice; upserts are keyed by chunk_id, so the stored
result stays idempotent.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.embeddings.local import get_embedder
from app.adapters.vectorstore.milvus import MilvusStore, collection_name
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.knowledge.models import Chunk, Document, DocumentVersion, VectorIndex

INDEX_ERROR = "索引失败：请检查模型缓存、设备及 Milvus 服务"


def _job(db: Session, version_id: int) -> VectorIndex:
    job = db.scalar(
        select(VectorIndex).where(
            VectorIndex.version_id == version_id,
            VectorIndex.collection == collection_name(),
        )
    )
    if job is None:
        job = VectorIndex(version_id=version_id, collection=collection_name())
        db.add(job)
    return job


def index_version(version_id):
    with SessionLocal.begin() as db:
        version = db.get(DocumentVersion, version_id)
        if version is None or version.status != "parsed":
            return {"status": "not_parsed"}
        job = _job(db, version_id)
        if job.status == "indexed" and job.chunks_indexed:
            return {"status": "indexed", "chunks": job.chunks_indexed}
        document = db.get(Document, version.document_id)
        if document is None:
            return {"status": "not_parsed"}
        document_id, knowledge_base_id = document.id, document.knowledge_base_id
        rows = [
            (chunk.id, chunk.content)
            for chunk in db.scalars(
                select(Chunk).where(Chunk.version_id == version_id).order_by(Chunk.position)
            )
        ]
        job.status, job.error = "indexing", None

    store = None
    try:
        embedder = get_embedder()
        store = MilvusStore()
        store.ensure()
        size = get_settings().index_batch_size
        for start in range(0, len(rows), size):
            batch = rows[start : start + size]
            vectors = embedder.encode([content for _, content in batch])
            store.upsert(
                [
                    {
                        "chunk_id": chunk_id,
                        "version_id": version_id,
                        "document_id": document_id,
                        "knowledge_base_id": knowledge_base_id,
                        "vector": vector,
                    }
                    for (chunk_id, _), vector in zip(batch, vectors, strict=True)
                ]
            )
        status, error, count = "indexed", None, len(rows)
    except Exception:
        logging.getLogger(__name__).exception("Index failed for version %s", version_id)
        status, error, count = "failed", INDEX_ERROR, 0
    finally:
        if store:
            store.close()

    with SessionLocal.begin() as db:
        job = _job(db, version_id)
        job.status, job.error, job.chunks_indexed = status, error, count
    return {"status": status, "chunks": count}
