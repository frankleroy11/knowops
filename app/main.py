from fastapi import FastAPI

from app.core.config import get_settings
from app.modules.health.router import router
from app.modules.knowledge.router import router as knowledge_router

app = FastAPI(
    title=get_settings().app_name,
    version="0.6.0",
    description=(
        "企业知识库问答平台：支持知识库创建、文档上传与异步解析。支持 BGE-M3 语义检索；"
        "支持 Qwen 带来源引用问答；支持 API Token 认证与知识库成员授权（AUTH_MODE=off/enforced，"
        "默认 off 即单机本地管理员）。前端登录与审核发布流程见后续阶段。"
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
