"""FAQ 优先匹配与缓存状态快照；所有候选先经过 SQL 权限和版本筛选。"""

import hashlib
import json
import math

from fastapi import HTTPException
from sqlalchemy import func, select

from app.adapters.embeddings.local import get_embedder
from app.adapters.llm.qwen import SYSTEM_PROMPT
from app.adapters.vectorstore.milvus import collection_name
from app.core.config import get_settings
from app.modules.auth import service as auth
from app.modules.faq.models import Faq
from app.modules.knowledge.models import (
    Chunk,
    Document,
    DocumentVersion,
    KnowledgeBase,
    VectorIndex,
)


def normalize(text):
    # 只折叠空白和大小写，不删掉数字、否定词、单位或标点，避免不同问题被合并。
    return " ".join(text.split()).casefold()


def digest(data):
    return hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True, default=str).encode()
    ).hexdigest()


def context(db, principal, body):
    """先验证权限，再生成当前可用资料的快照；即使缓存命中也必须执行。"""
    if body.scope == "all":
        kb_ids = auth.authorized_kb_ids(db, principal)
    else:
        auth.require_kb(db, principal, body.knowledge_base_id, "read")
        kb_ids = [body.knowledge_base_id]
    versions = list(
        db.execute(
            select(
                DocumentVersion.id,
                Document.id,
                Document.filename,
                KnowledgeBase.id,
                KnowledgeBase.name,
            )
            .join(Document, DocumentVersion.document_id == Document.id)
            .join(KnowledgeBase, Document.knowledge_base_id == KnowledgeBase.id)
            .join(VectorIndex, VectorIndex.version_id == DocumentVersion.id)
            .where(
                Document.knowledge_base_id.in_(kb_ids),
                Document.retired_at.is_(None),
                DocumentVersion.status == "parsed",
                DocumentVersion.is_current.is_(True),
                DocumentVersion.review_status == "approved",
                VectorIndex.status == "indexed",
                VectorIndex.collection == collection_name(),
            )
            .order_by(DocumentVersion.id)
        )
    )
    ids = [row[0] for row in versions]
    # 应用重新解析会创建新的块 ID；计数及最大 ID 让旧结果缓存自动失效。
    chunks = db.execute(
        select(func.count(Chunk.id), func.max(Chunk.id)).where(Chunk.version_id.in_(ids))
    ).one()
    entries = list(
        db.execute(
            select(Faq, Chunk, Document, KnowledgeBase)
            .join(Chunk, Faq.chunk_id == Chunk.id)
            .join(DocumentVersion, Chunk.version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .join(KnowledgeBase, Document.knowledge_base_id == KnowledgeBase.id)
            .where(
                Chunk.version_id.in_(ids),
                Faq.knowledge_base_id == Document.knowledge_base_id,
            )
            .order_by(Faq.id)
        )
    )
    s = get_settings()
    identity = {
        "user": [principal.id, principal.tenant_id, principal.role, principal.local],
        "kb_ids": kb_ids,
        "versions": [list(row) for row in versions],
        "chunks": list(chunks),
        "faqs": [
            [
                f.id,
                f.question,
                f.answer,
                f.quote,
                f.chunk_id,
                f.enabled,
                f.embedding_identity,
                f.question_vector,
            ]
            for f, *_ in entries
        ],
        "model": [
            s.llm_model,
            s.llm_base_url,
            collection_name(),
            SYSTEM_PROMPT,
            s.embedding_model_path,
            s.reranker_model,
            s.reranker_model_path,
            s.reranker_max_length,
        ],
        "policy": [s.faq_enabled, s.faq_similarity_threshold, s.faq_similarity_margin],
        "request": body.model_dump(),
    }
    return {
        "entries": entries,
        "version_ids": ids,
        "kb_ids": kb_ids,
        "cache_key": "knowops:answer:v1:" + digest(identity),
    }


def cosine(left, right):
    # 不依赖向量是否已经归一化；错误维度、非有限数或零向量都不能命中。
    try:
        if len(left) != len(right) or not left:
            return -1.0
        if not all(math.isfinite(x) for x in [*left, *right]):
            return -1.0
        denominator = math.sqrt(sum(x * x for x in left) * sum(x * x for x in right))
        return (
            sum(a * b for a, b in zip(left, right, strict=True)) / denominator
            if denominator
            else -1.0
        )
    except (TypeError, ValueError, OverflowError):
        return -1.0


def match(question, state):
    """精确匹配优先，未命中才编码；阈值及领先差距不足时继续走 RAG。"""
    s = get_settings()
    if not s.faq_enabled or not state["entries"]:
        return None
    entries = [
        row
        for row in state["entries"]
        if row[0].enabled and " ".join(row[0].quote.split()) in " ".join(row[1].content.split())
    ]
    exact = [row for row in entries if normalize(row[0].question) == normalize(question)]
    if exact:
        # 同一问题在多个库有不同答案时不替用户选择口径，回退 RAG。
        if len({normalize(row[0].answer) for row in exact}) != 1:
            return None
        winner, score, method = exact[0], 1.0, "exact"
    else:
        candidates = [row for row in entries if row[0].embedding_identity == collection_name()]
        # 演示使用 SQL 内向量做有界扫描；规模扩大后改用独立 FAQ 向量索引。
        if not candidates or len(candidates) > 1000:
            return None
        try:
            vector = get_embedder().encode([question], is_query=True)[0]
        except Exception:  # noqa: BLE001 - FAQ optimization must not replace RAG error handling
            return None
        ranked = sorted(
            [(cosine(vector, row[0].question_vector), row) for row in candidates],
            key=lambda item: item[0],
            reverse=True,
        )
        score, winner = ranked[0]
        if score < s.faq_similarity_threshold:
            return None
        if len(ranked) > 1 and score - ranked[1][0] < s.faq_similarity_margin:
            return None
        method = "semantic"
    faq, chunk, doc, kb = winner
    citation = {
        "source_id": 1,
        "chunk_id": chunk.id,
        "version_id": chunk.version_id,
        "document_id": doc.id,
        "knowledge_base_id": kb.id,
        "knowledge_base_name": kb.name,
        "filename": doc.filename,
        "position": chunk.position,
        "page": chunk.page,
        "content": chunk.content,
    }
    return {
        "answer": faq.answer,
        "answerable": True,
        "citations": [citation],
        "claims": [{"text": faq.answer, "evidence": [{"source_id": 1, "quote": faq.quote}]}],
        "grounding_status": "faq_reviewed",
        "answer_source": "faq",
        "faq_id": faq.id,
        "faq_match": method,
        "faq_score": round(score, 6),
        "context_chunk_count": 1,
        "context_expanded": False,
    }


def validate_source(db, kb_id, chunk_id, quote):
    row = db.execute(
        select(Chunk, DocumentVersion, Document)
        .join(DocumentVersion, Chunk.version_id == DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .join(VectorIndex, VectorIndex.version_id == DocumentVersion.id)
        .where(
            Chunk.id == chunk_id,
            Document.knowledge_base_id == kb_id,
            Document.retired_at.is_(None),
            DocumentVersion.is_current.is_(True),
            DocumentVersion.status == "parsed",
            DocumentVersion.review_status == "approved",
            VectorIndex.collection == collection_name(),
            VectorIndex.status == "indexed",
        )
    ).first()
    if (
        row is None
        or not normalize(quote)
        or " ".join(quote.split()) not in " ".join(row[0].content.split())
    ):
        raise HTTPException(422, "请选择当前已审核且索引完成的证据块，并逐字摘录证据")
    return row[0]
