import logging

from sqlalchemy import select

from app.adapters.embeddings.local import get_embedder
from app.adapters.vectorstore.milvus import MilvusStore, collection_name
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.knowledge.models import Chunk, Document, DocumentVersion, VectorIndex


def index_version(version_id):
    store = None
    try:
        with SessionLocal.begin() as db:
            # Serialize duplicate jobs using the durable version row.
            version = db.scalar(
                select(DocumentVersion).where(DocumentVersion.id == version_id).with_for_update()
            )
            if version is None or version.status != "parsed":
                return {"status": "not_parsed"}
            job = db.scalar(
                select(VectorIndex).where(
                    VectorIndex.version_id == version_id,
                    VectorIndex.collection == collection_name(),
                )
            )
            if job is None:
                job = VectorIndex(version_id=version_id, collection=collection_name())
                db.add(job)
            chunks = list(
                db.scalars(
                    select(Chunk).where(Chunk.version_id == version_id).order_by(Chunk.position)
                )
            )
            document = db.get(Document, version.document_id)
            try:
                embedder = get_embedder()
                store = MilvusStore()
                store.ensure()
                size = get_settings().index_batch_size
                for start in range(0, len(chunks), size):
                    batch = chunks[start : start + size]
                    vectors = embedder.encode([c.content for c in batch])
                    store.upsert(
                        [
                            {
                                "chunk_id": c.id,
                                "version_id": version_id,
                                "document_id": document.id,
                                "knowledge_base_id": document.knowledge_base_id,
                                "vector": v,
                            }
                            for c, v in zip(batch, vectors, strict=True)
                        ]
                    )
                job.status, job.error = "indexed", None
                job.chunks_indexed = len(chunks)
            except Exception:
                logging.getLogger(__name__).exception("Index failed for version %s", version_id)
                job.status, job.error = "failed", "索引失败：请检查模型缓存、设备及 Milvus 服务"
                job.chunks_indexed = 0
            return {"status": job.status, "chunks": job.chunks_indexed}
    finally:
        if store:
            store.close()
