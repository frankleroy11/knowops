from typing import Literal

from fastapi import APIRouter, HTTPException, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.storage import (
    FileTooLarge,
    LocalStorage,
    StorageError,
    StoredFile,
    UnsupportedFormat,
)
from app.adapters.vectorstore.milvus import collection_name
from app.core.config import ROOT, get_settings
from app.db.deps import DB, get_db  # noqa: F401 - re-exported for existing imports
from app.modules.audit import service as audit
from app.modules.auth import service
from app.modules.auth.deps import CurrentPrincipal
from app.modules.auth.principal import Principal
from app.modules.knowledge import review
from app.modules.knowledge.models import (
    Chunk,
    Document,
    DocumentVersion,
    KnowledgeBase,
    VectorIndex,
)
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


class KBDelete(BaseModel):
    confirm_name: str = Field(min_length=1, max_length=128)


class KBUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
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
    old_name = kb.name
    if body.name is not None:
        service.require_admin(principal)
        if not body.name.strip():
            raise HTTPException(422, "名称不能为空")
        kb.name = body.name.strip()
    if body.description is not None:
        kb.description = body.description
    if body.review_required is not None:
        kb.review_required = body.review_required
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "知识库名称已存在") from None
    audit.record(
        db,
        principal,
        "kb.rename" if kb.name != old_name else "kb.update",
        "knowledge_base",
        kb.id,
        f"old_name={old_name} name={kb.name} review_required={kb.review_required}",
    )
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "review_required": kb.review_required,
        "tenant_id": kb.tenant_id,
        "my_role": service.kb_role(db, principal, kb.id),
    }


@router.delete("/knowledge-bases/{kb_id}")
def delete_kb(kb_id: int, body: KBDelete, db: DB, principal: CurrentPrincipal):
    from app.modules.knowledge.management import delete_knowledge_base

    try:
        return delete_knowledge_base(db, principal, kb_id, body.confirm_name, storage_backend())
    except StorageError:
        raise HTTPException(409, "存储路径异常，删除已阻止，请联系管理员") from None


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


def dispatch(version, db=None):
    try:
        task = ingest_document.delay(version.id)
        return {"queued": True, "task_id": task.id}
    except Exception:  # noqa: BLE001 - retain a retryable state on broker failure
        if db is not None:
            version.status, version.error = "failed", "任务未入队，请重试解析"
            db.commit()
        return {"queued": False, "task_id": None}


def storage_backend() -> LocalStorage:
    """Storage rooted at the project directory (tests patch `knowledge.ROOT`)."""
    return LocalStorage(ROOT, MAX_BYTES)


def store_upload(file: UploadFile) -> StoredFile:
    """Persist one upload; the HTTP layer only maps storage errors to status codes."""
    try:
        return storage_backend().save(file)
    except UnsupportedFormat as exc:
        raise HTTPException(415, str(exc)) from None
    except FileTooLarge as exc:
        raise HTTPException(413, str(exc)) from None
    except StorageError as exc:
        raise HTTPException(422, str(exc)) from None


@router.post("/knowledge-bases/{kb_id}/documents", status_code=202)
def upload(kb_id: int, file: UploadFile, db: DB, principal: CurrentPrincipal):
    kb = service.require_kb(db, principal, kb_id, "write")
    stored = store_upload(file)
    doc = Document(knowledge_base_id=kb_id, filename=stored.filename, uploaded_by=principal.id)
    db.add(doc)
    db.flush()
    version = DocumentVersion(
        document_id=doc.id,
        version=1,
        content_hash=stored.content_hash,
        storage_path=stored.storage_name,
        chunk_strategy=get_settings().chunk_strategy,
        chunk_size=get_settings().chunk_size,
        chunk_overlap=get_settings().chunk_overlap,
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
        f"kb={kb_id} filename={stored.filename} review={status}",
    )
    queue = dispatch(version, db)
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
    doc = db.scalar(
        select(Document).where(Document.id == document_id).execution_options(populate_existing=True)
    )
    if doc is None:
        raise HTTPException(404, "文档不存在")
    stored = store_upload(file)
    latest = (
        db.scalar(
            select(func.max(DocumentVersion.version)).where(DocumentVersion.document_id == doc.id)
        )
        or 0
    )
    version = DocumentVersion(
        document_id=doc.id,
        version=latest + 1,
        content_hash=stored.content_hash,
        storage_path=stored.storage_name,
        chunk_strategy=get_settings().chunk_strategy,
        chunk_size=get_settings().chunk_size,
        chunk_overlap=get_settings().chunk_overlap,
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
        f"version={version.version} filename={stored.filename} review={status}",
    )
    queue = dispatch(version, db)
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
    version = db.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.id == version_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if version is None:
        raise HTTPException(404, "版本不存在")
    if version.status != "failed":
        raise HTTPException(409, "仅可重试解析失败的版本，等待中的任务请勿重复投递")
    version.status = "pending"
    db.commit()
    result = dispatch(version, db)
    if not result["queued"]:
        version.status = "failed"
        db.commit()
        raise HTTPException(503, "任务队列不可用，失败状态已保留，请稍后重试")
    audit.record(
        db, principal, "version.retry", "document_version", version_id, f"document={document.id}"
    )
    return {"version_id": version_id, **result}


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
            "chunk_strategy": v.chunk_strategy,
            "chunk_size": v.chunk_size,
            "chunk_overlap": v.chunk_overlap,
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
def review_version(version_id: int, body: ReviewIn, db: DB, principal: CurrentPrincipal):
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


class DocumentDelete(BaseModel):
    confirm_filename: str = Field(min_length=1, max_length=255)


@router.delete("/documents/{document_id}")
def delete_document(document_id: int, body: DocumentDelete, db: DB, principal: CurrentPrincipal):
    from app.modules.knowledge import operations

    try:
        return operations.delete_document(
            db, principal, document_id, body.confirm_filename, storage_backend()
        )
    except StorageError:
        raise HTTPException(409, "存储路径异常，已阻止删除") from None


@router.get("/documents/{document_id}/versions")
def document_versions(document_id: int, db: DB, principal: CurrentPrincipal):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    service.require_kb(db, principal, doc.knowledge_base_id, "read")
    rows = db.execute(
        select(DocumentVersion, VectorIndex)
        .outerjoin(
            VectorIndex,
            (VectorIndex.version_id == DocumentVersion.id)
            & (VectorIndex.collection == collection_name()),
        )
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version.desc())
    ).all()
    return [
        {
            "version_id": v.id,
            "chunk_strategy": v.chunk_strategy,
            "chunk_size": v.chunk_size,
            "chunk_overlap": v.chunk_overlap,
            "version": v.version,
            "status": v.status,
            "error": v.error,
            "review_status": v.review_status,
            "is_current": v.is_current,
            "index_status": i.status if i else "pending",
            "index_error": i.error if i else None,
        }
        for v, i in rows
    ]


@router.post("/document-versions/{version_id}/publish")
def publish_version(version_id: int, db: DB, principal: CurrentPrincipal):
    from app.modules.knowledge.operations import locked_document

    v = review.load_version(db, version_id)
    doc, kb = locked_document(db, principal, v.document_id)
    v = db.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.id == version_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if v is None:
        raise HTTPException(404, "版本不存在")
    index = db.scalar(
        select(VectorIndex).where(
            VectorIndex.version_id == version_id, VectorIndex.collection == collection_name()
        )
    )
    if (
        v.status != "parsed"
        or not index
        or index.status != "indexed"
        or v.review_status != "approved"
    ):
        raise HTTPException(409, "仅可发布已解析、已索引且审核通过的版本")
    # Publish and its audit must commit together.
    for other in db.scalars(select(DocumentVersion).where(DocumentVersion.document_id == doc.id)):
        other.is_current = other.id == version_id
    doc.retired_at = None
    audit.record(
        db,
        principal,
        "version.publish",
        "document_version",
        version_id,
        f"document={doc.id} version={v.version}",
        tenant_id=kb.tenant_id,
    )
    return {"version_id": v.id, "is_current": True}


@router.get("/admin/document-failures")
def document_failures(db: DB, principal: CurrentPrincipal, limit: int = 50, offset: int = 0):
    service.require_admin(principal)
    scope = service.authorized_kb_ids(db, principal)
    from sqlalchemy import or_

    rows = db.execute(
        select(DocumentVersion, Document, KnowledgeBase, VectorIndex)
        .join(Document, Document.id == DocumentVersion.document_id)
        .join(KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id)
        .outerjoin(
            VectorIndex,
            (VectorIndex.version_id == DocumentVersion.id)
            & (VectorIndex.collection == collection_name()),
        )
        .where(
            KnowledgeBase.id.in_(scope),
            or_(DocumentVersion.status == "failed", VectorIndex.status == "failed"),
        )
        .order_by(DocumentVersion.id.desc())
        .offset(max(0, offset))
        .limit(min(max(limit, 1), 100))
    ).all()
    return [
        {
            "id": d.id,
            "version_id": v.id,
            "chunk_strategy": v.chunk_strategy,
            "chunk_size": v.chunk_size,
            "chunk_overlap": v.chunk_overlap,
            "version": v.version,
            "filename": d.filename,
            "knowledge_base_id": kb.id,
            "knowledge_base_name": kb.name,
            "status": v.status,
            "index_status": i.status if i else "pending",
            "stage": "parse" if v.status == "failed" else "index",
            "error": v.error if v.status == "failed" else i.error,
        }
        for v, d, kb, i in rows
    ]
