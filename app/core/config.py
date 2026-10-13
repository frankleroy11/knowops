from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    app_name: str = "KnowOps"
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 13306
    mysql_database: str = "knowops"
    mysql_user: str = "knowops"
    mysql_password: str = ""
    redis_url: str = "redis://127.0.0.1:16379/0"
    milvus_uri: str = "http://127.0.0.1:19540"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""

    # --- Embedding 适配器 ---
    # provider: bge_m3 = 真实本地模型；hash = 无模型依赖的确定性假向量，仅用于测试与离线开发
    embedder_provider: str = "bge_m3"
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    embedding_batch_size: int = Field(default=4, ge=1, le=64)
    embedding_max_length: int = Field(default=1024, ge=1, le=8192)
    # 本地模型目录（可选）。为空时按 embedding_model 交给 sentence-transformers 解析
    embedding_model_path: str = ""

    # --- Milvus 索引 ---
    milvus_collection_prefix: str = "knowops_chunks"
    index_batch_size: int = Field(default=64, ge=1, le=256)
    index_max_retries: int = 3

    @property
    def milvus_timeout(self) -> float:
        return 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
