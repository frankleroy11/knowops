"""Audit trail access, partitioned by tenant."""

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
    tenant_id: int | None
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
    tenant_id: int | None = None,
):
    """Platform administrators see every tenant (optionally filtered);
    tenant administrators only ever see their own trail."""
    if principal.is_platform_admin:
        scope = tenant_id
    else:
        if principal.tenant_id is None:
            raise HTTPException(403, "当前账号未绑定租户")
        if tenant_id is not None and tenant_id != principal.tenant_id:
            raise HTTPException(403, "无权查看其他租户的审计日志")
        scope = principal.tenant_id
    return [
        AuditOut(
            id=entry.id,
            actor_id=entry.actor_id,
            actor_email=entry.actor_email,
            tenant_id=entry.tenant_id,
            action=entry.action,
            object_type=entry.object_type,
            object_id=entry.object_id,
            detail=entry.detail,
            created_at=entry.created_at.isoformat() if entry.created_at else None,
        )
        for entry in audit.list_entries(
            db,
            limit=limit,
            offset=offset,
            action=action,
            object_type=object_type,
            tenant_id=scope,
        )
    ]
