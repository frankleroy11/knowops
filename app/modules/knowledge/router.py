import hashlib
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import ROOT
from app.db.deps import DB, get_db  # noqa: F401 - re-exported for existing imports
from app.modules.audit import service as audit
from app.modules.auth import service
from app.modules.auth.deps import CurrentPrincipal
from app.modules.auth.principal import Principal
from app.modules.knowledge import review
from app.modules.knowledge.models import Chunk, Document, DocumentVersion, KnowledgeBase
from app.modules.tenant import service as tenants
from app.workers.celery_app import ingest_document

router = APIRouter(tags=["知识库与文档"])
MAX_BYTES = 10 * 1024 * 1024
KB_MEMBER_ROLES = ("owner", "editor", "viewer")


class KBCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=512)
    review_required: bool = False
    tenant_id: int | None = None


class KBUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=512)
    review_required: bool | None = None


class ReviewIn(BaseModel):
    decision: Literal["approve", "reject"]
    note: str = Field(default="", max_length=512)


class KBOut(KBCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    my_role: str | None = None


class MemberIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: Literal["owner", "editor", "viewer"] = "viewer"


class MemberOut(BaseModel):
    user_id: int
    email: str
    display_name: str
    role: str


def resolve_kb_tenant(db, principal, requested: int | None) -> int:
    """Tenant members always create inside their own tenant; platform admins choose
    explicitly or fall back to the default tenant."""
    if principal.is_platform_admin:
        tenant_id = requested
        if tenant_id is None:
            fallback = tenants.default_tenant(db)
            if fallback is None:
                raise HTTPException(422, "请先创建租户")
            tenant_id = fallback.id
        tenants.get_tenant(db, tenant_id)
        return tenant_id
    if principal.tenant_id is None:
        raise HTTPException(403, "当前账号未绑定租户，无法创建知识库")
    return principal.tenant_id


@router.post("/knowledge-bases", response_model=KBOut, status_code=201)
def create_kb(body: KBCreate, db: DB, principal: CurrentPrincipal):
    if not body.name.strip():
        raise HTTPException(422, "名称不能为空")
    service.require_author(principal)
    tenant_id = resolve_kb_tenant(db, principal, body.tenant_id)
    kb = KnowledgeBase(
        name=body.name.strip(),
        description=body.description,
        owner_id=principal.id,
        review_required=body.review_required,
        tenant_id=tenant_id,
    )
    db.add(kb)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "知识库名称已存在") from exc
    if principal.id is not None:
        service.ensure_membership(db, kb.id, principal.id, "owner")
    audit.record(
        db,
        principal,
        "kb.create",
        "knowledge_base",
        kb.id,
        f"name={kb.name} tenant={tenant_id} review_required={kb.review_required}",
    )
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "review_required": kb.review_required,
        "tenant_id": kb.tenant_id,
        "my_role": "admin" if principal.is_admin else ("owner" if principal.id else None),
    }


@router.patch("/knowledge-bases/{kb_id}", response_model=KBOut)
def update_kb(kb_id: int, body: KBUpdate, db: DB, principal: CurrentPrincipal):
    kb = service.require_kb(db, principal, kb_id, "write")
    if body.description is not None:
        kb.description = body.description
    if body.review_required is not None:
        kb.review_required = body.review_required
    db.commit()
    audit.record(
        db,
        principal,
        "kb.update",
        "knowledge_base",
        kb.id,
        f"review_required={kb.review_required}",
    )
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "review_required": kb.review_required,
        "tenant_id": kb.tenant_id,
        "my_role": service.kb_role(db, principal, kb.id),
    }


@router.get("/knowledge-bases", response_model=list[KBOut])
def list_kbs(db: DB, principal: CurrentPrincipal, limit: int = 50, offset: int = 0):
    scope = service.authorized_kb_ids(db, principal)
    if not scope:
        return []
    roles = service.membership_roles(db, principal)
    return [
        {
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "review_required": kb.review_required,
            "tenant_id": kb.tenant_id,
            "my_role": "admin" if principal.is_admin else roles.get(kb.id),
        }
        for kb in db.scalars(
            select(KnowledgeBase)
            .where(KnowledgeBase.id.in_(scope))
            .order_by(KnowledgeBase.id)
            .offset(max(0, offset))
            .limit(min(max(1, limit), 100))
        )
    ]


def dispatch(version):
    try:
        task = ingest_document.delay(version.id)
        return {"queued": True, "task_id": task.id}
    except Exception:  # noqa: BLE001 - persist pending state if broker is unavailable
        return {"queued": False, "task_id": None}


def store_upload(file: UploadFile) -> tuple[str, str, str]:
    """Persist one uploaded file; returns (filename, stored_name, sha256)."""
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
        committed = True
    finally:
        file.file.close()
        if not committed:
            target.unlink(missing_ok=True)
    return name, target.name, digest.hexdigest()


@router.post("/knowledge-bases/{kb_id}/documents", status_code=202)
def upload(kb_id: int, file: UploadFile, db: DB, principal: CurrentPrincipal):
    kb = service.require_kb(db, principal, kb_id, "write")
    name, storage_name, content_hash = store_upload(file)
    doc = Document(knowledge_base_id=kb_id, filename=name, uploaded_by=principal.id)
    db.add(doc)
    db.flush()
    version = DocumentVersion(
        document_id=doc.id,
        version=1,
        content_hash=content_hash,
        storage_path=storage_name,
        uploaded_by=principal.id,
    )
    db.add(version)
    db.commit()
    status = review.apply_initial_status(db, principal, kb, doc, version)
    audit.record(
        db,
        principal,
        "document.upload",
        "document",
        doc.id,
        f"kb={kb_id} filename={name} review={status}",
    )
    queue = dispatch(version)
    return {
        "document_id": doc.id,
        "version_id": version.id,
        "status": "pending",
        "review_status": status,
        "is_current": version.is_current,
        **queue,
    }


@router.post("/documents/{document_id}/versions", status_code=202)
def upload_version(document_id: int, file: UploadFile, db: DB, principal: CurrentPrincipal):
    """New version of an existing document; the old version stays live until publish."""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    kb = service.require_kb(db, principal, doc.knowledge_base_id, "write")
    name, storage_name, content_hash = store_upload(file)
    latest = (
        db.scalar(select(func.max(DocumentVersion.version)).where(DocumentVersion.document_id == doc.id))
        or 0
    )
    version = DocumentVersion(
        document_id=doc.id,
        version=latest + 1,
        content_hash=content_hash,
        storage_path=storage_name,
        uploaded_by=principal.id,
    )
    db.add(version)
    db.commit()
    status = review.apply_initial_status(db, principal, kb, doc, version)
    audit.record(
        db,
        principal,
        "document.version.upload",
        "document",
        doc.id,
        f"version={version.version} filename={name} review={status}",
    )
    queue = dispatch(version)
    return {
        "document_id": doc.id,
        "version_id": version.id,
        "version": version.version,
        "status": "pending",
        "review_status": status,
        "is_current": version.is_current,
        **queue,
    }


@router.post("/documents/{document_id}/retire")
def retire_document(document_id: int, db: DB, principal: CurrentPrincipal):
    """Take a document out of retrieval without deleting its chunks or vectors."""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    service.require_kb(db, principal, doc.knowledge_base_id, "write")
    review.retire(db, principal, doc)
    return {
        "document_id": doc.id,
        "retired_at": doc.retired_at.isoformat() if doc.retired_at else None,
    }


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
        "review_status": version.review_status,
        "is_current": version.is_current,
        "retired_at": doc.retired_at.isoformat() if doc.retired_at else None,
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
            "version": v.version,
            "status": v.status,
            "error": v.error,
            "chunk_count": count or 0,
            "index_status": index.status if index else "pending",
            "index_error": index.error if index else None,
            "review_status": v.review_status,
            "is_current": v.is_current,
            "retired_at": d.retired_at.isoformat() if d.retired_at else None,
        }
        for d, v, index, count in rows
    ]


@router.get("/knowledge-bases/{kb_id}/documents")
def list_documents(
    kb_id: int, db: DB, principal: CurrentPrincipal, limit: int = 50, offset: int = 0
):
    return documents(kb_id, db, limit=limit, offset=offset, principal=principal)


@router.get("/knowledge-bases/{kb_id}/members", response_model=list[MemberOut])
def list_kb_members(kb_id: int, db: DB, principal: CurrentPrincipal):
    service.require_kb(db, principal, kb_id, "write")
    return service.list_members(db, kb_id)


@router.post("/knowledge-bases/{kb_id}/members", response_model=MemberOut, status_code=201)
def add_kb_member(kb_id: int, body: MemberIn, db: DB, principal: CurrentPrincipal):
    kb = service.require_kb(db, principal, kb_id, "write")
    user = service.find_user_by_email(db, body.email)
    if user is None or user.tenant_id != kb.tenant_id:
        # Cross-tenant users are hidden rather than disclosed.
        raise HTTPException(404, "用户不存在，请先创建用户")
    service.ensure_membership(db, kb_id, user.id, body.role)
    if body.role == "owner" and kb.owner_id is None:
        kb.owner_id = user.id
        db.commit()
    audit.record(
        db,
        principal,
        "kb.member.grant",
        "knowledge_base",
        kb_id,
        f"user={user.email} role={body.role}",
    )
    return {
        "user_id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": body.role,
    }


@router.delete("/knowledge-bases/{kb_id}/members/{user_id}", status_code=204)
def remove_kb_member(kb_id: int, user_id: int, db: DB, principal: CurrentPrincipal):
    service.require_kb(db, principal, kb_id, "write")
    service.remove_membership(db, kb_id, user_id)
    audit.record(db, principal, "kb.member.revoke", "knowledge_base", kb_id, f"user_id={user_id}")
    return Response(status_code=204)


@router.get("/knowledge-bases/{kb_id}/reviews")
def list_reviews(kb_id: int, db: DB, principal: CurrentPrincipal):
    service.require_kb(db, principal, kb_id, "write")
    return review.pending_versions(db, kb_id)


@router.post("/document-versions/{version_id}/review")
def review_version(
    version_id: int, body: ReviewIn, db: DB, principal: CurrentPrincipal
):
    version = review.load_version(db, version_id)
    document = review.document_of(db, version)
    service.require_kb(db, principal, document.knowledge_base_id, "write")
    if body.decision == "approve":
        review.approve(db, principal, version, body.note)
    else:
        review.reject(db, principal, version, body.note)
    return {
        "version_id": version.id,
        "document_id": document.id,
        "review_status": version.review_status,
        "is_current": version.is_current,
    }
