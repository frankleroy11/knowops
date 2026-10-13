import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import ROOT
from app.db.deps import DB, get_db  # noqa: F401 - re-exported for existing imports
from app.modules.auth import service
from app.modules.auth.deps import CurrentPrincipal
from app.modules.auth.principal import Principal
from app.modules.knowledge.models import Chunk, Document, DocumentVersion, KnowledgeBase
from app.workers.celery_app import ingest_document

router = APIRouter(tags=["知识库与文档"])
MAX_BYTES = 10 * 1024 * 1024


class KBCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=512)


class KBOut(KBCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


@router.post("/knowledge-bases", response_model=KBOut, status_code=201)
def create_kb(body: KBCreate, db: DB, principal: CurrentPrincipal):
    if not body.name.strip():
        raise HTTPException(422, "名称不能为空")
    service.require_author(principal)
    kb = KnowledgeBase(name=body.name.strip(), description=body.description, owner_id=principal.id)
    db.add(kb)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "知识库名称已存在") from exc
    if principal.id is not None:
        service.ensure_membership(db, kb.id, principal.id, "owner")
    return kb


@router.get("/knowledge-bases", response_model=list[KBOut])
def list_kbs(db: DB, principal: CurrentPrincipal, limit: int = 50, offset: int = 0):
    scope = service.authorized_kb_ids(db, principal)
    if not scope:
        return []
    return list(
        db.scalars(
            select(KnowledgeBase)
            .where(KnowledgeBase.id.in_(scope))
            .order_by(KnowledgeBase.id)
            .offset(max(0, offset))
            .limit(min(max(1, limit), 100))
        )
    )


def dispatch(version):
    try:
        task = ingest_document.delay(version.id)
        return {"queued": True, "task_id": task.id}
    except Exception:  # noqa: BLE001 - persist pending state if broker is unavailable
        return {"queued": False, "task_id": None}


@router.post("/knowledge-bases/{kb_id}/documents", status_code=202)
def upload(kb_id: int, file: UploadFile, db: DB, principal: CurrentPrincipal):
    service.require_kb(db, principal, kb_id, "write")
    name = (file.filename or "").replace("\\", "/").split("/")[-1]
    suffix = Path(name).suffix.lower()
    if suffix not in {".txt", ".md", ".pdf"}:
        raise HTTPException(415, "仅支持 TXT、Markdown、文本 PDF")
    if len(name) > 255:
        raise HTTPException(422, "文件名过长")
    directory = ROOT / "storage"
    directory.mkdir(exist_ok=True)
    target = directory / (uuid4().hex + suffix)
    digest = hashlib.sha256()
    total = 0
    committed = False
    try:
        with target.open("xb") as output:
            while data := file.file.read(64 * 1024):
                total += len(data)
                if total > MAX_BYTES:
                    raise HTTPException(413, "文件不能超过 10 MiB")
                digest.update(data)
                output.write(data)
        if total == 0:
            raise HTTPException(422, "文件为空")
        doc = Document(knowledge_base_id=kb_id, filename=name, uploaded_by=principal.id)
        db.add(doc)
        db.flush()
        version = DocumentVersion(
            document_id=doc.id, version=1, content_hash=digest.hexdigest(), storage_path=target.name
        )
        db.add(version)
        db.commit()
        committed = True
    finally:
        file.file.close()
        if not committed:
            target.unlink(missing_ok=True)
    queue = dispatch(version)
    return {"document_id": doc.id, "version_id": version.id, "status": "pending", **queue}


@router.get("/documents/{document_id}")
def detail(document_id: int, db: DB, principal: CurrentPrincipal):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    service.require_kb(db, principal, doc.knowledge_base_id, "read")
    version = db.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc.id)
        .order_by(DocumentVersion.version.desc())
        .limit(1)
    )
    count = db.scalar(select(func.count()).select_from(Chunk).where(Chunk.version_id == version.id))
    return {
        "id": doc.id,
        "filename": doc.filename,
        "knowledge_base_id": doc.knowledge_base_id,
        "version_id": version.id,
        "version": version.version,
        "status": version.status,
        "error": version.error,
        "chunk_count": count,
    }


@router.get("/document-versions/{version_id}/chunks")
def list_chunks(
    version_id: int, db: DB, principal: CurrentPrincipal, limit: int = 20, offset: int = 0
):
    version = db.get(DocumentVersion, version_id)
    if version is None:
        raise HTTPException(404, "版本不存在")
    document = db.get(Document, version.document_id)
    if document is None:
        raise HTTPException(404, "文档不存在")
    service.require_kb(db, principal, document.knowledge_base_id, "read")
    chunks = db.scalars(
        select(Chunk)
        .where(Chunk.version_id == version_id)
        .order_by(Chunk.position)
        .offset(max(0, offset))
        .limit(min(max(1, limit), 100))
    )
    return [
        {"id": c.id, "position": c.position, "page": c.page, "content": c.content} for c in chunks
    ]


@router.post("/document-versions/{version_id}/retry", status_code=202)
def retry(version_id: int, db: DB, principal: CurrentPrincipal):
    version = db.get(DocumentVersion, version_id)
    if version is None:
        raise HTTPException(404, "版本不存在")
    document = db.get(Document, version.document_id)
    if document is None:
        raise HTTPException(404, "文档不存在")
    service.require_kb(db, principal, document.knowledge_base_id, "write")
    if version.status == "parsed":
        raise HTTPException(409, "该版本已经解析完成")
    return {"version_id": version_id, **dispatch(version)}


def documents(
    kb_id: int,
    db: Session,
    limit: int = 50,
    offset: int = 0,
    principal: Principal | None = None,
):
    """Document list for one knowledge base; read access is checked here."""
    from app.adapters.vectorstore.milvus import collection_name
    from app.modules.knowledge.models import VectorIndex

    principal = service.default_principal() if principal is None else principal
    service.require_kb(db, principal, kb_id, "read")
    latest = (
        select(DocumentVersion.document_id, func.max(DocumentVersion.version).label("latest"))
        .group_by(DocumentVersion.document_id)
        .subquery()
    )
    counts = (
        select(Chunk.version_id, func.count(Chunk.id).label("total"))
        .group_by(Chunk.version_id)
        .subquery()
    )
    rows = db.execute(
        select(Document, DocumentVersion, VectorIndex, counts.c.total)
        .join(DocumentVersion, DocumentVersion.document_id == Document.id)
        .join(
            latest,
            (latest.c.document_id == Document.id) & (latest.c.latest == DocumentVersion.version),
        )
        .outerjoin(
            VectorIndex,
            (VectorIndex.version_id == DocumentVersion.id)
            & (VectorIndex.collection == collection_name()),
        )
        .outerjoin(counts, counts.c.version_id == DocumentVersion.id)
        .where(Document.knowledge_base_id == kb_id)
        .order_by(Document.id.desc())
        .offset(max(0, offset))
        .limit(min(max(1, limit), 100))
    )
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "version_id": v.id,
            "status": v.status,
            "error": v.error,
            "chunk_count": count or 0,
            "index_status": index.status if index else "pending",
            "index_error": index.error if index else None,
        }
        for d, v, index, count in rows
    ]


@router.get("/knowledge-bases/{kb_id}/documents")
def list_documents(
    kb_id: int, db: DB, principal: CurrentPrincipal, limit: int = 50, offset: int = 0
):
    return documents(kb_id, db, limit=limit, offset=offset, principal=principal)
