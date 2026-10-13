from fastapi import FastAPI

from app.core.config import get_settings
from app.modules.health.router import router
from app.modules.knowledge.router import router as knowledge_router

app = FastAPI(
    title=get_settings().app_name,
    version="0.5.0",
    description="企业知识库问答平台：支持知识库创建、文档上传与异步解析。支持 BGE-M3 语义检索；支持 Qwen 带来源引用问答；鉴权待实现。",
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


from fastapi.staticfiles import StaticFiles

from app.core.config import ROOT

frontend_dist = ROOT / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/ui", StaticFiles(directory=frontend_dist, html=True), name="ui")
