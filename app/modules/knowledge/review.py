# 中文导读：
# 审核与发布状态机：待审核版本保留旧版本的可用性；通过、拒绝、下架和发布分别改变业务状态，检索还需检查索引是否就绪

"""Submit → review → publish workflow, plus retire (下架) semantics.

Retrieval only serves a version when it is parsed, indexed, `is_current` and
`review_status == "approved"`. Publishing a version retires the previous current
version of the same document; retiring a document clears its current version
without deleting chunks or vectors, so history stays auditable.
"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit import service as audit
from app.modules.knowledge.models import (
    REVIEW_APPROVED,
    REVIEW_PENDING,
    REVIEW_REJECTED,
    Document,
    DocumentVersion,
    KnowledgeBase,
)


def initial_review_status(kb: KnowledgeBase, principal) -> str:
    """Admins publish directly; other uploads wait when the KB requires review."""
    if not kb.review_required or principal.is_admin:
        return REVIEW_APPROVED
    return REVIEW_PENDING


def current_version(db: Session, document_id: int) -> DocumentVersion | None:
    return db.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == document_id,
            DocumentVersion.is_current.is_(True),
        )
    )


# 选择文档的当前版本；真正进入检索还需同时满足审核与索引条件。
def publish(db: Session, document: Document, version: DocumentVersion) -> None:
    for other in db.scalars(
        select(DocumentVersion).where(
            DocumentVersion.document_id == document.id,
            DocumentVersion.id != version.id,
            DocumentVersion.is_current.is_(True),
        )
    ):
        other.is_current = False
    version.is_current = True
    document.retired_at = None
    db.commit()


def apply_initial_status(
    db: Session, principal, kb: KnowledgeBase, document: Document, version: DocumentVersion
) -> str:
    """Publish immediately, or keep the version out of retrieval until reviewed."""
    status = initial_review_status(kb, principal)
    version.review_status = status
    if status == REVIEW_APPROVED:
        publish(db, document, version)
    else:
        version.is_current = False
        db.commit()
    return status


def load_version(db: Session, version_id: int) -> DocumentVersion:
    version = db.get(DocumentVersion, version_id)
    if version is None:
        raise HTTPException(404, "版本不存在")
    return version


def document_of(db: Session, version: DocumentVersion) -> Document:
    document = db.get(Document, version.document_id)
    if document is None:
        raise HTTPException(404, "文档不存在")
    return document


def guard_reviewer(principal, version: DocumentVersion) -> None:
    if version.uploaded_by is not None and version.uploaded_by == principal.id and not principal.is_admin:
        raise HTTPException(409, "不能审核自己提交的版本，请由其他成员处理")


# 审核通过后更新发布状态；审核者身份限制仍由服务端检查。
def approve(db: Session, principal, version: DocumentVersion, note: str = "") -> DocumentVersion:
    guard_reviewer(principal, version)
    if version.review_status == REVIEW_APPROVED:
        raise HTTPException(409, "该版本已通过审核")
    document = document_of(db, version)
    version.review_status = REVIEW_APPROVED
    version.reviewed_by = principal.id
    version.reviewed_at = datetime.now()
    version.review_note = note or None
    db.commit()
    publish(db, document, version)
    audit.record(
        db,
        principal,
        "version.approve",
        "document_version",
        version.id,
        f"document={document.id} version={version.version}",
    )
    return version


# 拒绝本次版本，避免把未通过审核的内容暴露给检索。
def reject(db: Session, principal, version: DocumentVersion, note: str = "") -> DocumentVersion:
    guard_reviewer(principal, version)
    if version.review_status == REVIEW_REJECTED:
        raise HTTPException(409, "该版本已被驳回")
    document = document_of(db, version)
    version.review_status = REVIEW_REJECTED
    version.is_current = False
    version.reviewed_by = principal.id
    version.reviewed_at = datetime.now()
    version.review_note = note or None
    db.commit()
    audit.record(
        db,
        principal,
        "version.reject",
        "document_version",
        version.id,
        f"document={document.id} version={version.version} note={note}"[:512],
    )
    return version


# 下架后清除文档当前版本，已有向量也不能绕过业务过滤重新进入问答。
def retire(db: Session, principal, document: Document) -> None:
    version = current_version(db, document.id)
    if version is not None:
        version.is_current = False
    document.retired_at = datetime.now()
    db.commit()
    audit.record(
        db,
        principal,
        "document.retire",
        "document",
        document.id,
        f"kb={document.knowledge_base_id} filename={document.filename}"[:512],
    )


def pending_versions(db: Session, kb_id: int) -> list[dict]:
    rows = db.execute(
        select(DocumentVersion, Document)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(
            Document.knowledge_base_id == kb_id,
            DocumentVersion.review_status == REVIEW_PENDING,
        )
        .order_by(DocumentVersion.id)
    ).all()
    return [
        {
            "version_id": version.id,
            "document_id": document.id,
            "filename": document.filename,
            "version": version.version,
            "status": version.status,
            "uploaded_by": version.uploaded_by,
            "created_at": version.created_at.isoformat() if version.created_at else None,
        }
        for version, document in rows
    ]
