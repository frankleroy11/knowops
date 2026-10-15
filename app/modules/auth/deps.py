# 中文导读：
# 认证依赖：从请求解析当前身份，并为需要管理员权限的路由提供统一入口
# 接口隐藏按钮不能替代这里的服务端检查

"""FastAPI dependencies for authentication and coarse-grained authorization."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.db.deps import DB
from app.modules.auth import service
from app.modules.auth.principal import Principal


# 统一解析请求身份，让后续接口基于同一个身份对象执行授权。
def current_principal(
    db: DB,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    return service.resolve_principal(db, authorization)


CurrentPrincipal = Annotated[Principal, Depends(current_principal)]


# 管理员校验由后端执行，不能依赖前端页面是否显示管理入口。
def require_admin(principal: CurrentPrincipal) -> Principal:
    if not principal.is_admin:
        raise HTTPException(403, "需要管理员权限")
    return principal


AdminPrincipal = Annotated[Principal, Depends(require_admin)]
