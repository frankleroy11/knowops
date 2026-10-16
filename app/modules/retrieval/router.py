# 中文导读：
# 检索与索引接口：先计算可访问的当前有效版本，再进行向量召回并复核数据库状态；可选重排在召回后执行

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.embeddings.local import get_embedder
from app.adapters.vectorstore.milvus import MilvusStore, collection_name
from app.db.deps import DB
from app.modules.auth import service
from app.modules.auth.deps import CurrentPrincipal
from app.modules.auth.principal import Principal
from app.modules.knowledge.models import (
    Chunk,
    Document,
    DocumentVersion,
    KnowledgeBase,
    VectorIndex,
)

# 路由统一由 app.main 挂到 /api/v1；本文件内路径不重复写该前缀。
router = APIRouter(tags=["语义检索"])


# 请求模型集中约束查询范围和数量，非法组合在进入检索业务前即被拒绝。
class Query(BaseModel):
    # min_length 不排除全空格，search 中还会对 strip() 后的内容检查一次。
    query: str = Field(min_length=1, max_length=2000)
    # 单库模式必须提供 ID；all 模式必须省略 ID，含义是当前用户可读的全部库。
    knowledge_base_id: int | None = Field(default=None, gt=0)
    scope: Literal["knowledge_base", "all"] = "knowledge_base"
    # top_k 为最终最多返回的条数；权限复核可能过滤结果，实际条数可以更少。
    top_k: int = Field(default=5, ge=1, le=50)
    # 默认直接采用向量排序；开启重排时先召回 candidate_k 个候选，再选 top_k。
    rerank: bool = False
    candidate_k: int = Field(default=10, ge=1, le=50)
    # 0 表示不限制单文档数量；非零用于重排后的文档多样性控制。
    max_per_document: int = Field(default=0, ge=0, le=50)

    # 跨字段约束必须在所有字段解析后检查，避免范围与参数互相矛盾。
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


# 索引入队前检查状态，投递失败必须反馈失败，避免长期停留在索引中。
@router.post("/document-versions/{version_id}/index", status_code=202)
def enqueue_index(version_id: int, db: DB, principal: CurrentPrincipal):
    # 在接口调用时导入任务，避免仅加载路由就引入整个 Worker 初始化流程。
    from app.workers.celery_app import index_document

    # 先找到版本及所属文档，再检查该知识库的访问权限。
    version = db.get(DocumentVersion, version_id)
    if version is None:
        raise HTTPException(404, "版本不存在")
    document = db.get(Document, version.document_id)
    if document is None:
        raise HTTPException(404, "文档不存在")
    # 索引是写操作，只有能编辑该知识库的身份才允许手动投递。
    service.require_kb(db, principal, document.knowledge_base_id, "write")
    # 锁住版本行，并刷新会话中已读取的对象，避免用等待加锁前的旧状态决策。
    version = db.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.id == version_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if version is None or version.status != "parsed":
        raise HTTPException(409, "请先完成解析")
    # 索引状态按“版本 + 当前编码配置对应的集合”区分，不能借用其他模型的完成状态。
    job = db.scalar(
        select(VectorIndex)
        .where(VectorIndex.version_id == version_id, VectorIndex.collection == collection_name())
        .with_for_update()
    )
    # 已处理或正在处理时拒绝重复入队；不存在或失败的任务允许继续创建／重试。
    if job and job.status in {"indexing", "indexed"}:
        raise HTTPException(409, "索引正在处理或已经完成，请勿重复投递")
    if job is None:
        job = VectorIndex(version_id=version_id, collection=collection_name())
        db.add(job)
    # 先写入索引中状态并提交，Worker 才能读取；SQL 提交与消息投递并非原子事务。
    job.status, job.error = "indexing", None
    db.commit()
    try:
        # 202 和 queued 仅表示队列接受任务，不表示编码或 Milvus 写入已经完成。
        task = index_document.delay(version_id)
        return {"version_id": version_id, "queued": True, "task_id": task.id}
    except Exception:  # noqa: BLE001 - sanitize external service failures
        # 这里只补偿明确捕获到的投递异常；进程在提交后中断的情况不由此分支恢复。
        job.status, job.error = "failed", "任务未入队，请重试索引"
        db.commit()
        raise HTTPException(503, "任务队列不可用，请重试") from None


# 查询状态也需要知识库读权限；不能只凭版本 ID 向其他用户暴露处理信息。
@router.get("/document-versions/{version_id}/index")
def index_status(version_id: int, db: DB, principal: CurrentPrincipal):
    version = db.get(DocumentVersion, version_id)
    if version is None:
        raise HTTPException(404, "版本不存在")
    document = db.get(Document, version.document_id)
    if document is None:
        raise HTTPException(404, "文档不存在")
    service.require_kb(db, principal, document.knowledge_base_id, "read")
    job = db.scalar(
        select(VectorIndex).where(
            VectorIndex.version_id == version_id, VectorIndex.collection == collection_name()
        )
    )
    # 没有当前集合的状态记录时展示 pending；chunks_indexed 是记录值，并非实时统计 Milvus。
    return {
        "version_id": version_id,
        "collection": collection_name(),
        "status": job.status if job else "pending",
        "chunks_indexed": job.chunks_indexed if job else 0,
        "error": job.error if job else None,
    }


# SQL 先确定当前、已批准且索引就绪的版本，Milvus 执行预过滤，返回后再次检查业务状态。
def search(body: Query, db: Session, principal: Principal | None = None):
    """Authorized semantic search.

    `scope="all"` never means "every row": it expands only to the knowledge bases
    the caller may read, and an explicitly requested knowledge base without access
    is rejected with 403 instead of being silently filtered out.
    """
    # HTTP 路由传入认证身份；内部调用未传身份时遵循认证服务的默认身份策略。
    principal = service.default_principal() if principal is None else principal
    if not body.query.strip():
        raise HTTPException(422, "查询不能为空")
    # all 扩展到当前用户可读的库；单库明确无权访问时返回 403，不悄悄改查其他库。
    if body.scope == "all":
        kb_ids = service.authorized_kb_ids(db, principal)
    else:
        service.require_kb(db, principal, body.knowledge_base_id, "read")
        kb_ids = [body.knowledge_base_id]
    # 没有可读知识库时直接返回空结果，避免加载模型或发起无范围的向量查询。
    if not kb_ids:
        return {
            "query": body.query,
            "collection": collection_name(),
            "scope": body.scope,
            "reranked": body.rerank,
            "hits": [],
        }
    # SQL 是可检索状态的权威：仅选未下架文档的当前、已批准、已解析且已索引版本。
    # 将版本白名单传给 Milvus 预过滤，避免无效旧版本占用 top_k 名额。
    eligible_versions = list(
        db.scalars(
            select(DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .join(VectorIndex, VectorIndex.version_id == DocumentVersion.id)
            .where(
                Document.knowledge_base_id.in_(kb_ids),
                Document.retired_at.is_(None),
                DocumentVersion.status == "parsed",
                DocumentVersion.is_current.is_(True),
                DocumentVersion.review_status == "approved",
                VectorIndex.collection == collection_name(),
                VectorIndex.status == "indexed",
            )
        )
    )
    # 有知识库权限但尚无就绪版本，也不需要编码查询或访问 Milvus。
    if not eligible_versions:
        return {
            "query": body.query,
            "collection": collection_name(),
            "scope": body.scope,
            "reranked": body.rerank,
            "hits": [],
        }
    store = None
    try:
        # 查询与入库共用编码器及集合配置；一次传入一个查询，取回对应向量。
        vector = get_embedder().encode([body.query], is_query=True)[0]
        store = MilvusStore()
        hits = store.search(
            vector,
            kb_ids if body.scope == "all" else body.knowledge_base_id,
            body.candidate_k if body.rerank else body.top_k,
            version_ids=eligible_versions,
        )
        # Milvus 只提供块 ID 和相似度；正文、文件名及归属从 SQL 读取。
        results = []
        # 逐条复核业务状态，丢弃查不到正文或已不符合当前版本条件的向量命中。
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
                    DocumentVersion.is_current.is_(True),
                    DocumentVersion.review_status == "approved",
                    VectorIndex.collection == collection_name(),
                    VectorIndex.status == "indexed",
                )
            ).first()
            if row:
                chunk, doc, kb_name = row
                results.append(
                    {
                        "chunk_id": chunk.id,
                        # 这里是 Milvus 余弦相似度分数，不是答案正确率或置信概率。
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
        # 重排只能重新选择召回候选，无法恢复第一阶段未召回的内容。
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
        # 详细异常写服务端日志，对客户端只返回统一说明，避免暴露服务内部错误。
        logging.getLogger(__name__).exception("Semantic search failed")
        raise HTTPException(503, "检索不可用：请检查模型及 Milvus 服务") from None
    finally:
        # 无论检索是否成功，都释放本次 Milvus 客户端连接。
        if store:
            store.close()


# HTTP 入口注入请求级 SQL 会话与认证身份，统一复用上面的 search 业务。
@router.post("/search")
def search_endpoint(body: Query, db: DB, principal: CurrentPrincipal):
    return search(body, db, principal)
