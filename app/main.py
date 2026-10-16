# 中文导读：
# FastAPI 应用入口：汇总业务路由，并在前端构建产物存在时挂载页面
# 任务解析和向量化由独立 Celery Worker 执行

from fastapi import FastAPI

from app.core.config import get_settings
from app.modules.health.router import router
from app.modules.knowledge.router import router as knowledge_router

app = FastAPI(
    title=get_settings().app_name,
    version="0.7.0",
    description=(
        "企业知识库问答平台：支持多租户、账号认证与成员授权、文档异步解析和 BGE-M3/Milvus 检索。"
        "支持审核发布、版本切换、失败重试、资料删除、统一问答与逐事实引用校验、反馈和审计。"
        "AUTH_MODE=enforced 启用登录；off 为本地免鉴权管理员模式。"
    ),
)
app.include_router(router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def index():
    return {"project": "KnowOps", "docs": "/docs", "stage": "rag-chat"}


from app.modules.retrieval.router import router as retrieval_router

app.include_router(retrieval_router, prefix="/api/v1")

from app.modules.chat.router import router as chat_router

app.include_router(chat_router, prefix="/api/v1")

from app.modules.auth.router import router as auth_router

app.include_router(auth_router, prefix="/api/v1")

from app.modules.audit.router import router as audit_router

app.include_router(audit_router, prefix="/api/v1")

from app.modules.tenant.router import router as tenant_router

app.include_router(tenant_router, prefix="/api/v1")

from app.modules.oidc.router import router as oidc_router

app.include_router(oidc_router, prefix="/api/v1")

from app.modules.feedback.router import router as feedback_router

app.include_router(feedback_router, prefix="/api/v1")


from fastapi.staticfiles import StaticFiles

from app.core.config import ROOT

frontend_dist = ROOT / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/ui", StaticFiles(directory=frontend_dist, html=True), name="ui")

from app.modules.system.router import router as system_router

app.include_router(system_router, prefix="/api/v1")

from app.modules.faq.router import router as faq_router

app.include_router(faq_router, prefix="/api/v1")
