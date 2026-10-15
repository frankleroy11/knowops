"""Single-use OIDC login state, stored durably so several workers can serve the flow."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class OidcLoginState(Base):
    __tablename__ = "oidc_login_states"
    state: Mapped[str] = mapped_column(String(64), primary_key=True)
    nonce: Mapped[str] = mapped_column(String(64))
    web: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
