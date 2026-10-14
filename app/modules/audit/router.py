"""Administrator access to the audit trail."""

from typing import Annotated

from fastapi import APIRouter, HTTPException
from fastapi import Query as QueryParam
from pydantic import BaseModel

from app.db.deps import DB
from app.modules.audit import service as audit
from app.modules.auth.deps import AdminPrincipal

router = APIRouter(tags=["审计日志"])


class AuditOut(BaseModel):
    id: int
    actor_id: int | None
    actor_email: str
    action: str
    object_type: str
    object_id: int | None
    detail: str
    created_at: str | None


@router.get("/admin/audit-logs", response_model=list[AuditOut])
def list_audit_logs(
    db: DB,
    principal: AdminPrincipal,
    limit: Annotated[int, QueryParam(ge=1, le=200)] = 50,
    offset: Annotated[int, QueryParam(ge=0)] = 0,
    action: str | None = None,
    object_type: str | None = None,
):
    """Platform administrators only: rows are not yet partitioned by tenant, so a
    tenant administrator must not be able to read another tenant's trail."""
    if not principal.is_platform_admin:
        raise HTTPException(403, "需要平台管理员权限")
    return [
        AuditOut(
            id=entry.id,
            actor_id=entry.actor_id,
            actor_email=entry.actor_email,
            action=entry.action,
            object_type=entry.object_type,
            object_id=entry.object_id,
            detail=entry.detail,
            created_at=entry.created_at.isoformat() if entry.created_at else None,
        )
        for entry in audit.list_entries(
            db, limit=limit, offset=offset, action=action, object_type=object_type
        )
    ]
