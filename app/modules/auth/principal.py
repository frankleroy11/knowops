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
    local: bool = False

    @property
    def is_admin(self) -> bool:
        return self.role == ADMIN

    @property
    def can_author(self) -> bool:
        """May create knowledge bases and upload documents."""
        return self.role in (ADMIN, EDITOR)


LOCAL_ADMIN = Principal(
    id=None,
    email="local@localhost",
    role=ADMIN,
    display_name="本地管理员",
    local=True,
)
