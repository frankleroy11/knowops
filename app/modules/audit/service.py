# 中文导读：
# 审计记录与保留期清理
# record 会提交当前数据库事务，因此调用前必须完成业务校验，并把需要原子提交的变更放在同一会话中

"""Write and read the audit trail.

`record` commits on its own so a successful business action is never left
untraced by an unrelated later rollback. Actor identity is snapshotted as text
so entries stay readable after a user row is renamed or removed.

Every entry carries the tenant that owns the affected object, so a tenant
administrator can read their own trail without seeing another tenant's. The
tenant is derived from the object (not from the actor), because a platform
administrator acting on tenant A's knowledge base must still produce an entry
that tenant A can see.
"""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog


def _tenant_of_object(db: Session, object_type: str, object_id: int | None) -> int | None:
    if object_id is None:
        return None
    if object_type == "tenant":
        return object_id
    if object_type == "knowledge_base":
        from app.modules.knowledge.models import KnowledgeBase

        kb = db.get(KnowledgeBase, object_id)
        return kb.tenant_id if kb else None
    if object_type == "document":
        from app.modules.knowledge.models import Document, KnowledgeBase

        document = db.get(Document, object_id)
        if document is None:
            return None
        kb = db.get(KnowledgeBase, document.knowledge_base_id)
        return kb.tenant_id if kb else None
    if object_type == "document_version":
        from app.modules.knowledge.models import Document, DocumentVersion, KnowledgeBase

        version = db.get(DocumentVersion, object_id)
        document = db.get(Document, version.document_id) if version else None
        if document is None:
            return None
        kb = db.get(KnowledgeBase, document.knowledge_base_id)
        return kb.tenant_id if kb else None
    if object_type == "user":
        from app.modules.auth.models import User

        user = db.get(User, object_id)
        return user.tenant_id if user else None
    return None


# 审计与当前业务修改一起提交；调用者不能在此之后再补做会导致操作失败的关键校验。
def record(
    db: Session,
    actor,
    action: str,
    object_type: str = "",
    object_id: int | None = None,
    detail: str = "",
    tenant_id: int | None = None,
) -> AuditLog:
    if tenant_id is None:
        tenant_id = _tenant_of_object(db, object_type, object_id)
    if tenant_id is None:
        tenant_id = getattr(actor, "tenant_id", None)
    entry = AuditLog(
        # 用 API 时钟写入：保留策略与导出都按同一时钟比较，避免 DB(UTC) 与本地混用
        created_at=datetime.now(),
        actor_id=getattr(actor, "id", None),
        actor_email=getattr(actor, "email", "") or "",
        tenant_id=tenant_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        detail=detail[:512],
    )
    db.add(entry)
    db.commit()
    return entry


def list_entries(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    action: str | None = None,
    object_type: str | None = None,
    tenant_id: int | None = None,
    max_limit: int = 200,
) -> list[AuditLog]:
    query = select(AuditLog).order_by(AuditLog.id.desc())
    if tenant_id is not None:
        query = query.where(AuditLog.tenant_id == tenant_id)
    if action:
        query = query.where(AuditLog.action == action)
    if object_type:
        query = query.where(AuditLog.object_type == object_type)
    return list(db.scalars(query.offset(max(0, offset)).limit(min(max(1, limit), max_limit))))


# 按截止时间清理日志，调用方负责选择预览或实际删除以及权限范围。
def prune(db: Session, before: datetime) -> int:
    """删除 `before` 之前的审计记录（保留策略由调用方决定天数）。"""
    result = db.execute(delete(AuditLog).where(AuditLog.created_at < before))
    db.commit()
    return result.rowcount or 0
