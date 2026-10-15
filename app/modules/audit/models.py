# 中文导读：
# 审计日志表：保存操作者、对象与操作快照，供管理端追溯；业务对象删除后仍需保留操作记录

"""Audit trail for every state-changing action."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

# `tenants` is referenced below; importing it keeps the table registered for
# foreign-key resolution in every process (Celery included).
from app.modules.tenant import models as tenant_models  # noqa: F401


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    actor_email: Mapped[str] = mapped_column(String(255), default="")
    # Owning tenant of the affected object; NULL for platform-level entries.
    tenant_id: Mapped[int | None] = mapped_column(
        ForeignKey("tenants.id"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64), index=True)
    object_type: Mapped[str] = mapped_column(String(32), default="")
    object_id: Mapped[int | None] = mapped_column(nullable=True)
    detail: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
