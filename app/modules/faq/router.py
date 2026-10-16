"""FAQ 管理接口：管理员人工确认答案，必须绑定自己有权管理的有效证据。"""

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select

from app.adapters.embeddings.local import get_embedder
from app.adapters.vectorstore.milvus import collection_name
from app.db.deps import DB
from app.modules.audit import service as audit
from app.modules.auth import service as auth
from app.modules.auth.deps import AdminPrincipal
from app.modules.faq.models import Faq
from app.modules.faq.service import validate_source
from app.modules.knowledge.models import Chunk, Document, DocumentVersion, VectorIndex

router = APIRouter(tags=["高频问题管理"])


class FaqIn(BaseModel):
    knowledge_base_id: int = Field(gt=0)
    chunk_id: int = Field(gt=0)
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=2000)
    quote: str = Field(min_length=1, max_length=1200)
    enabled: bool = True

    @field_validator("question", "answer", "quote")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("问题、答案和证据不能为空")
        return value.strip()


def output(db, row):
    try:
        validate_source(db, row.knowledge_base_id, row.chunk_id, row.quote)
        valid = True
    except HTTPException:
        valid = False
    return {
        "id": row.id,
        "knowledge_base_id": row.knowledge_base_id,
        "chunk_id": row.chunk_id,
        "question": row.question,
        "answer": row.answer,
        "quote": row.quote,
        "enabled": row.enabled,
        "source_valid": valid,
    }


@router.get("/admin/faqs/sources")
def sources(
    db: DB, principal: AdminPrincipal, knowledge_base_id: int, offset: int = Query(default=0, ge=0)
):
    auth.require_kb(db, principal, knowledge_base_id, "write")
    rows = db.execute(
        select(Chunk, Document.filename)
        .join(DocumentVersion, Chunk.version_id == DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .join(VectorIndex, VectorIndex.version_id == DocumentVersion.id)
        .where(
            Document.knowledge_base_id == knowledge_base_id,
            Document.retired_at.is_(None),
            DocumentVersion.is_current.is_(True),
            DocumentVersion.status == "parsed",
            DocumentVersion.review_status == "approved",
            VectorIndex.status == "indexed",
            VectorIndex.collection == collection_name(),
        )
        .order_by(Chunk.id)
        .offset(offset)
        .limit(100)
    ).all()
    return [
        {"chunk_id": c.id, "filename": name, "position": c.position, "content": c.content}
        for c, name in rows
    ]


@router.get("/admin/faqs")
def list_faqs(
    db: DB, principal: AdminPrincipal, knowledge_base_id: int, offset: int = Query(default=0, ge=0)
):
    auth.require_kb(db, principal, knowledge_base_id, "write")
    rows = db.scalars(
        select(Faq)
        .where(Faq.knowledge_base_id == knowledge_base_id)
        .order_by(Faq.id.desc())
        .offset(offset)
        .limit(50)
    )
    return [output(db, row) for row in rows]


def save(db, principal, body, row=None):
    auth.require_kb(db, principal, body.knowledge_base_id, "write")
    if row is not None:
        auth.require_kb(db, principal, row.knowledge_base_id, "write")
    validate_source(db, body.knowledge_base_id, body.chunk_id, body.quote)
    # 小规模 FAQ 使用 SQL 中的问题向量；限制每库容量，避免无界扫描。
    if row is None or row.knowledge_base_id != body.knowledge_base_id:
        count = db.scalar(
            select(func.count())
            .select_from(Faq)
            .where(Faq.knowledge_base_id == body.knowledge_base_id)
        )
        if count >= 200:
            raise HTTPException(409, "每个知识库最多维护 200 条 FAQ")
    identity = collection_name()
    # 仅修改答案／启停时复用问题向量，停用不能依赖模型服务恰好可用。
    reuse = (
        row is not None
        and row.question == body.question
        and (row.embedding_identity == identity or not body.enabled)
    )
    if reuse:
        vector, identity = row.question_vector, row.embedding_identity
    else:
        try:
            vector = get_embedder().encode([body.question], is_query=True)[0]
        except Exception:  # noqa: BLE001 - do not leak model paths
            raise HTTPException(503, "FAQ 问题编码失败，请检查嵌入模型") from None
    if row is None:
        row = Faq()
        db.add(row)
    for name, value in body.model_dump().items():
        setattr(row, name, value)
    row.question_vector = vector
    row.embedding_identity = identity
    db.flush()
    audit.record(
        db, principal, "faq.save", "knowledge_base", body.knowledge_base_id, f"faq_id={row.id}"
    )
    return output(db, row)


@router.post("/admin/faqs", status_code=201)
def create_faq(body: FaqIn, db: DB, principal: AdminPrincipal):
    return save(db, principal, body)


@router.put("/admin/faqs/{faq_id}")
def update_faq(faq_id: int, body: FaqIn, db: DB, principal: AdminPrincipal):
    row = db.get(Faq, faq_id)
    if row is None:
        raise HTTPException(404, "FAQ 不存在")
    return save(db, principal, body, row)


@router.delete("/admin/faqs/{faq_id}", status_code=204)
def delete_faq(faq_id: int, db: DB, principal: AdminPrincipal):
    row = db.get(Faq, faq_id)
    if row is None:
        raise HTTPException(404, "FAQ 不存在")
    auth.require_kb(db, principal, row.knowledge_base_id, "write")
    kb_id = row.knowledge_base_id
    db.delete(row)
    audit.record(db, principal, "faq.delete", "knowledge_base", kb_id, f"faq_id={faq_id}")
    return Response(status_code=204)
