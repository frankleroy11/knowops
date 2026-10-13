from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    """语义检索请求。knowledge_base_id 为空表示只在本机开发环境下跨全部知识库检索。"""

    query: str = Field(min_length=1, max_length=2000)
    knowledge_base_id: int | None = None
    top_k: int = Field(default=5, ge=1, le=50)


class ChunkHit(BaseModel):
    chunk_id: int
    score: float = Field(description="COSINE 相似度，越大越相似")
    document_id: int
    filename: str
    version_id: int
    position: int
    page: int | None = None
    content: str


class SearchResponse(BaseModel):
    query: str
    top_k: int
    knowledge_base_id: int | None = None
    collection: str = Field(description="本次检索使用的 Milvus collection")
    embedder: str = Field(description="本次检索使用的模型标识")
    dim: int
    hits: list[ChunkHit]


class IndexJob(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_id: int
    status: str = Field(description="pending / indexed / failed，与解析状态相互独立")
    chunks_total: int = 0
    chunks_indexed: int = 0
    error: str | None = None
