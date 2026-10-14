"""Tenant lookup and administration helpers."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.tenant.models import DEFAULT_SLUG, Tenant


def default_tenant(db: Session) -> Tenant | None:
    return db.scalar(select(Tenant).where(Tenant.slug == DEFAULT_SLUG))


def get_tenant(db: Session, tenant_id: int) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(404, "租户不存在")
    return tenant


def get_tenant_by_slug(db: Session, slug: str) -> Tenant:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == slug.strip().lower()))
    if tenant is None:
        raise HTTPException(404, f"租户不存在：{slug}")
    return tenant


def list_tenants(db: Session) -> list[Tenant]:
    return list(db.scalars(select(Tenant).order_by(Tenant.id)))


def create_tenant(db: Session, name: str, slug: str) -> Tenant:
    name, slug = name.strip(), slug.strip().lower()
    if not name or not slug:
        raise HTTPException(422, "租户名称与标识不能为空")
    if db.scalar(select(Tenant).where(Tenant.slug == slug)) is not None:
        raise HTTPException(409, "租户标识已存在")
    tenant = Tenant(name=name, slug=slug)
    db.add(tenant)
    db.commit()
    return tenant
