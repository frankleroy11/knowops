import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.adapters.embeddings.local import get_embedder
from app.adapters.vectorstore.milvus import MilvusStore, collection_name
from app.modules.knowledge.models import (
    Chunk,
    Document,
    DocumentVersion,
    KnowledgeBase,
    VectorIndex,
)
from app.modules.knowledge.router import DB

router = APIRouter(tags=["语义检索"])


class Query(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    knowledge_base_id: int = Field(gt=0)
    top_k: int = Field(default=5, ge=1, le=50)


@router.post("/document-versions/{version_id}/index", status_code=202)
def enqueue_index(version_id: int, db: DB):
    from app.workers.celery_app import index_document

    version = db.get(DocumentVersion, version_id)
    if version is None:
        raise HTTPException(404, "版本不存在")
    if version.status != "parsed":
        raise HTTPException(409, "请先完成解析")
    try:
        task = index_document.delay(version_id)
        return {"version_id": version_id, "queued": True, "task_id": task.id}
    except Exception:  # noqa: BLE001 - sanitize external service failures
        raise HTTPException(503, "任务队列不可用，请重试") from None


@router.get("/document-versions/{version_id}/index")
def index_status(version_id: int, db: DB):
    if db.get(DocumentVersion, version_id) is None:
        raise HTTPException(404, "版本不存在")
    job = db.scalar(
        select(VectorIndex).where(
            VectorIndex.version_id == version_id, VectorIndex.collection == collection_name()
        )
    )
    return {
        "version_id": version_id,
        "collection": collection_name(),
        "status": job.status if job else "pending",
        "chunks_indexed": job.chunks_indexed if job else 0,
        "error": job.error if job else None,
    }


@router.post("/search")
def search(body: Query, db: DB):
    if not body.query.strip():
        raise HTTPException(422, "查询不能为空")
    if db.get(KnowledgeBase, body.knowledge_base_id) is None:
        raise HTTPException(404, "知识库不存在")
    store = None
    try:
        vector = get_embedder().encode([body.query], is_query=True)[0]
        store = MilvusStore()
        hits = store.search(vector, body.knowledge_base_id, body.top_k)
        results = []
        for hit in hits:
            row = db.execute(
                select(Chunk, Document)
                .join(DocumentVersion, Chunk.version_id == DocumentVersion.id)
                .join(Document, DocumentVersion.document_id == Document.id)
                .join(VectorIndex, VectorIndex.version_id == DocumentVersion.id)
                .where(
                    Chunk.id == hit["chunk_id"],
                    Document.knowledge_base_id == body.knowledge_base_id,
                    DocumentVersion.status == "parsed",
                    VectorIndex.collection == collection_name(),
                    VectorIndex.status == "indexed",
                )
            ).first()
            if row:
                chunk, doc = row
                results.append(
                    {
                        "chunk_id": chunk.id,
                        "score": hit["distance"],
                        "document_id": doc.id,
                        "filename": doc.filename,
                        "version_id": chunk.version_id,
                        "position": chunk.position,
                        "page": chunk.page,
                        "content": chunk.content,
                    }
                )
        return {"query": body.query, "collection": collection_name(), "hits": results}
    except Exception:
        logging.getLogger(__name__).exception("Semantic search failed")
        raise HTTPException(503, "检索不可用：请检查模型及 Milvus 服务") from None
    finally:
        if store:
            store.close()
