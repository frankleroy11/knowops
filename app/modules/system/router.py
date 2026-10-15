# 中文导读：
# 平台运行状态接口：只允许平台管理员查看整体依赖和任务情况，普通租户管理员不能读取全局运行信息

from fastapi import APIRouter, HTTPException

from app.modules.auth.deps import CurrentPrincipal
from app.modules.system.service import snapshot

router = APIRouter(prefix="/admin/system", tags=["系统状态"])


@router.get("/status")
def system_status(principal: CurrentPrincipal):
    if not principal.is_platform_admin:
        raise HTTPException(403, "仅平台管理员可查看系统状态")
    return snapshot()
