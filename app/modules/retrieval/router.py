import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
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
    knowledge_base_id: int | None = Field(default=None, gt=0)
    scope: Literal["knowledge_base", "all"] = "knowledge_base"
    top_k: int = Field(default=5, ge=1, le=50)
    rerank: bool = False
    candidate_k: int = Field(default=10, ge=1, le=50)
    max_per_document: int = Field(default=0, ge=0, le=50)

    @model_validator(mode="after")
    def validate_candidates(self):
        if self.scope == "knowledge_base" and self.knowledge_base_id is None:
            raise ValueError("指定知识库提问需要 knowledge_base_id")
        if self.scope == "all" and self.knowledge_base_id is not None:
            raise ValueError("全部知识库模式不能同时指定 knowledge_base_id")
        if self.rerank and self.candidate_k < self.top_k:
            raise ValueError("重排序候选数不能小于 top_k")
        if self.max_per_document and not self.rerank:
            raise ValueError("文档多样性仅用于重排序")
        return self


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
    if body.scope == "all":
        kb_ids = list(db.scalars(select(KnowledgeBase.id)))
    else:
        if db.get(KnowledgeBase, body.knowledge_base_id) is None:
            raise HTTPException(404, "知识库不存在")
        kb_ids = [body.knowledge_base_id]
    if not kb_ids:
        return {
            "query": body.query,
            "collection": collection_name(),
            "scope": body.scope,
            "reranked": body.rerank,
            "hits": [],
        }
    store = None
    try:
        vector = get_embedder().encode([body.query], is_query=True)[0]
        store = MilvusStore()
        hits = store.search(
            vector,
            kb_ids if body.scope == "all" else body.knowledge_base_id,
            body.candidate_k if body.rerank else body.top_k,
        )
        results = []
        for hit in hits:
            row = db.execute(
                select(Chunk, Document, KnowledgeBase.name)
                .join(DocumentVersion, Chunk.version_id == DocumentVersion.id)
                .join(Document, DocumentVersion.document_id == Document.id)
                .join(KnowledgeBase, Document.knowledge_base_id == KnowledgeBase.id)
                .join(VectorIndex, VectorIndex.version_id == DocumentVersion.id)
                .where(
                    Chunk.id == hit["chunk_id"],
                    Document.knowledge_base_id.in_(kb_ids),
                    DocumentVersion.status == "parsed",
                    VectorIndex.collection == collection_name(),
                    VectorIndex.status == "indexed",
                )
            ).first()
            if row:
                chunk, doc, kb_name = row
                results.append(
                    {
                        "chunk_id": chunk.id,
                        "score": hit["distance"],
                        "document_id": doc.id,
                        "knowledge_base_id": doc.knowledge_base_id,
                        "knowledge_base_name": kb_name,
                        "filename": doc.filename,
                        "version_id": chunk.version_id,
                        "position": chunk.position,
                        "page": chunk.page,
                        "content": chunk.content,
                    }
                )
        if body.rerank:
            from app.adapters.reranker.local import rerank_hits

            results = rerank_hits(body.query, results, body.top_k, body.max_per_document)
        return {
            "query": body.query,
            "collection": collection_name(),
            "reranked": body.rerank,
            "scope": body.scope,
            "hits": results,
        }
    except Exception:
        logging.getLogger(__name__).exception("Semantic search failed")
        raise HTTPException(503, "检索不可用：请检查模型及 Milvus 服务") from None
    finally:
        if store:
            store.close()
