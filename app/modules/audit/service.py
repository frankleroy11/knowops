"""Write and read the audit trail.

`record` commits on its own so a successful business action is never left
untraced by an unrelated later rollback. Actor identity is snapshotted as text
so entries stay readable after a user row is renamed or removed.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog


def record(
    db: Session,
    actor,
    action: str,
    object_type: str = "",
    object_id: int | None = None,
    detail: str = "",
) -> AuditLog:
    entry = AuditLog(
        actor_id=getattr(actor, "id", None),
        actor_email=getattr(actor, "email", "") or "",
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
) -> list[AuditLog]:
    query = select(AuditLog).order_by(AuditLog.id.desc())
    if action:
        query = query.where(AuditLog.action == action)
    if object_type:
        query = query.where(AuditLog.object_type == object_type)
    return list(
        db.scalars(
            query.offset(max(0, offset)).limit(min(max(1, limit), 200))
        )
    )
