from fastapi import FastAPI

from app.core.config import get_settings
from app.modules.health.router import router
from app.modules.knowledge.router import router as knowledge_router

app = FastAPI(
    title=get_settings().app_name,
    version="0.3.0",
    description="企业知识库问答平台：支持知识库创建、文档上传与异步解析。支持 BGE-M3 语义检索；鉴权与问答生成待实现。",
)
app.include_router(router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def index():
    return {"project": "KnowOps", "docs": "/docs", "stage": "semantic-search"}


from app.modules.retrieval.router import router as retrieval_router

app.include_router(retrieval_router, prefix="/api/v1")
