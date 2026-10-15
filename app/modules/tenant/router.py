"""Tenant administration (platform administrators only)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.deps import DB
from app.modules.audit import service as audit
from app.modules.auth.deps import CurrentPrincipal
from app.modules.tenant import service as tenants

router = APIRouter(tags=["租户管理"])


class TenantIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    slug: str = Field(min_length=1, max_length=64)


class TenantOut(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool


def require_platform_admin(principal: CurrentPrincipal):
    if not principal.is_platform_admin:
        raise HTTPException(403, "需要平台管理员权限")
    return principal


@router.get("/admin/tenants", response_model=list[TenantOut])
def list_tenants(db: DB, principal: CurrentPrincipal):
    require_platform_admin(principal)
    return [
        TenantOut(id=t.id, name=t.name, slug=t.slug, is_active=t.is_active)
        for t in tenants.list_tenants(db)
    ]


@router.post("/admin/tenants", response_model=TenantOut, status_code=201)
def create_tenant(body: TenantIn, db: DB, principal: CurrentPrincipal):
    require_platform_admin(principal)
    tenant = tenants.create_tenant(db, body.name, body.slug)
    audit.record(db, principal, "tenant.create", "tenant", tenant.id, f"slug={tenant.slug}")
    return TenantOut(id=tenant.id, name=tenant.name, slug=tenant.slug, is_active=tenant.is_active)
