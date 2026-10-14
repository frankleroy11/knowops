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

    # --- 认证与授权 ---
    # off = 单机开发模式，所有请求视为本地管理员（保持历史行为）
    # enforced = 必须携带 Authorization: Bearer <token>，否则 401
    auth_mode: str = "off"

    # --- OIDC 单点登录（可选）---
    oidc_enabled: bool = False
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = ""
    oidc_scopes: str = "openid email profile"
    # 首次通过 SSO 登录时自动开通的本地账号属性
    oidc_default_role: str = "viewer"
    oidc_default_tenant_slug: str = "default"
    oidc_clock_skew: int = Field(default=60, ge=0, le=600)
    # 浏览器完成回调后跳回的前端地址
    oidc_web_redirect: str = "/ui/"

    # --- Embedding 适配器 ---
    # provider: bge_m3 = 真实本地模型；hash = 无模型依赖的确定性假向量，仅用于测试与离线开发
    embedder_provider: str = "bge_m3"
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    embedding_batch_size: int = Field(default=4, ge=1, le=64)
    embedding_max_length: int = Field(default=1024, ge=1, le=8192)
    # 本地模型目录（可选）。为空时按 embedding_model 交给 sentence-transformers 解析
    embedding_model_path: str = ""
    # 权重已缓存且机器离线时置 1：禁止联网做 HEAD 检查，避免加载卡住数分钟
    embedding_offline: bool = False

    # --- Milvus 索引 ---
    milvus_collection_prefix: str = "knowops_chunks"
    index_batch_size: int = Field(default=64, ge=1, le=256)
    index_max_retries: int = 3

    reranker_model: str = "BAAI/bge-reranker-base"
    reranker_model_path: str = ""
    reranker_max_length: int = Field(default=512, ge=32, le=512)
    reranker_batch_size: int = Field(default=4, ge=1, le=32)

    @property
    def milvus_timeout(self) -> float:
        return 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
