"""Audit trail access, partitioned by tenant."""

import csv
import io
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Response
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


def resolve_scope(principal, tenant_id: int | None) -> int | None:
    """平台管理员可按租户筛选；租户管理员只能看自己租户。"""
    if principal.is_platform_admin:
        return tenant_id
    if principal.tenant_id is None:
        raise HTTPException(403, "当前账号未绑定租户")
    if tenant_id is not None and tenant_id != principal.tenant_id:
        raise HTTPException(403, "无权查看其他租户的审计日志")
    return principal.tenant_id


@router.get("/admin/audit-logs/export")
def export_audit_logs(
    db: DB,
    principal: AdminPrincipal,
    format: Literal["csv", "json"] = "csv",
    action: str | None = None,
    object_type: str | None = None,
    tenant_id: int | None = None,
    limit: Annotated[int, QueryParam(ge=1, le=5000)] = 1000,
):
    """合规导出：CSV（默认，便于归档）或 JSON；范围与列表接口一致。"""
    entries = audit.list_entries(
        db,
        limit=limit,
        action=action,
        object_type=object_type,
        tenant_id=resolve_scope(principal, tenant_id),
        max_limit=5000,
    )
    if format == "json":
        return [
            {
                "id": e.id,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "actor_email": e.actor_email,
                "tenant_id": e.tenant_id,
                "action": e.action,
                "object_type": e.object_type,
                "object_id": e.object_id,
                "detail": e.detail,
            }
            for e in entries
        ]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["created_at", "actor_email", "tenant_id", "action", "object_type", "object_id", "detail"]
    )
    for e in entries:
        writer.writerow(
            [
                e.created_at.isoformat() if e.created_at else "",
                e.actor_email,
                e.tenant_id if e.tenant_id is not None else "",
                e.action,
                e.object_type,
                e.object_id if e.object_id is not None else "",
                e.detail,
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="knowops-audit-logs.csv"'},
    )


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
    scope = resolve_scope(principal, tenant_id)
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
