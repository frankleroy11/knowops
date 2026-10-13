import hashlib
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import ROOT
from app.db.session import SessionLocal
from app.modules.knowledge.models import Chunk, Document, DocumentVersion, KnowledgeBase
from app.workers.celery_app import ingest_document

router = APIRouter(tags=["知识库与文档"])
MAX_BYTES = 10 * 1024 * 1024


def get_db():
    with SessionLocal() as db:
        yield db


DB = Annotated[Session, Depends(get_db)]


class KBCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=512)


class KBOut(KBCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


@router.post("/knowledge-bases", response_model=KBOut, status_code=201)
def create_kb(body: KBCreate, db: DB):
    if not body.name.strip():
        raise HTTPException(422, "名称不能为空")
    kb = KnowledgeBase(name=body.name.strip(), description=body.description)
    db.add(kb)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "知识库名称已存在") from exc
    return kb


@router.get("/knowledge-bases", response_model=list[KBOut])
def list_kbs(db: DB, limit: int = 50, offset: int = 0):
    return list(
        db.scalars(
            select(KnowledgeBase)
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
def upload(kb_id: int, file: UploadFile, db: DB):
    if db.get(KnowledgeBase, kb_id) is None:
        raise HTTPException(404, "知识库不存在")
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
        doc = Document(knowledge_base_id=kb_id, filename=name)
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
def detail(document_id: int, db: DB):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
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
def list_chunks(version_id: int, db: DB, limit: int = 20, offset: int = 0):
    if db.get(DocumentVersion, version_id) is None:
        raise HTTPException(404, "版本不存在")
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
def retry(version_id: int, db: DB):
    version = db.get(DocumentVersion, version_id)
    if version is None:
        raise HTTPException(404, "版本不存在")
    if version.status == "parsed":
        raise HTTPException(409, "该版本已经解析完成")
    return {"version_id": version_id, **dispatch(version)}
