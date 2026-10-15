"""FastAPI dependencies for authentication and coarse-grained authorization."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.db.deps import DB
from app.modules.auth import service
from app.modules.auth.principal import Principal


def current_principal(
    db: DB,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    return service.resolve_principal(db, authorization)


CurrentPrincipal = Annotated[Principal, Depends(current_principal)]


def require_admin(principal: CurrentPrincipal) -> Principal:
    if not principal.is_admin:
        raise HTTPException(403, "需要管理员权限")
    return principal


AdminPrincipal = Annotated[Principal, Depends(require_admin)]
