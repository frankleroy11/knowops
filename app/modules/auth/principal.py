"""The caller identity used for authorization decisions."""

from dataclasses import dataclass

ADMIN = "admin"
EDITOR = "editor"
VIEWER = "viewer"


@dataclass(frozen=True)
class Principal:
    id: int | None
    email: str
    role: str
    display_name: str = ""
    tenant_id: int | None = None
    local: bool = False

    @property
    def is_admin(self) -> bool:
        """Role check only; use `is_platform_admin` for cross-tenant authority."""
        return self.role == ADMIN

    @property
    def is_platform_admin(self) -> bool:
        return self.role == ADMIN and self.tenant_id is None

    @property
    def can_author(self) -> bool:
        """May create knowledge bases and upload documents."""
        return self.role in (ADMIN, EDITOR)


LOCAL_ADMIN = Principal(
    id=None,
    email="local@localhost",
    role=ADMIN,
    display_name="本地管理员",
    tenant_id=None,
    local=True,
)
