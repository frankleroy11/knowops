# 中文导读：
# 集中读取环境配置并缓存设置对象
# 认证、公开注册和模型参数均在这里定义；本地环境文件中的密钥不应提交到仓库

from functools import lru_cache
from pathlib import Path
from typing import Literal

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
    public_registration_enabled: bool = False

    # FAQ 余弦阈值只是演示起点，需用真实语料校准；相近候选冲突时回退 RAG。
    faq_enabled: bool = True
    faq_similarity_threshold: float = Field(default=0.85, ge=0, le=1)
    faq_similarity_margin: float = Field(default=0.05, ge=0, le=1)
    answer_cache_enabled: bool = True
    answer_cache_ttl_seconds: int = Field(default=300, ge=1, le=86400)

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
    # JWKS 本地缓存秒数；kid 轮换时会在验签失败后强制刷新一次
    oidc_jwks_ttl_seconds: int = Field(default=600, ge=0, le=86400)
    # 从哪个声明读取用户组，以及组到本地角色的 JSON 映射
    oidc_role_claim: str = "groups"
    oidc_role_map: str = ""
    # 是否在每次登录按映射同步既有账号的角色（默认只影响新开通账号）
    oidc_role_sync: bool = False
    # 浏览器完成回调后跳回的前端地址
    oidc_web_redirect: str = "/ui/"
    # 单点登出后回跳地址；留空则复用 oidc_web_redirect
    oidc_post_logout_redirect: str = ""

    # --- 本地账号密码与 Token 生命周期 ---
    # 新签发 Token 的有效天数；0 表示不过期
    token_ttl_days: int = Field(default=30, ge=0, le=3650)
    # 演示可选明文存储；仓库默认仍为 scrypt，本机可在 .env 显式启用 plaintext。
    password_storage: Literal["scrypt", "plaintext"] = "scrypt"
    password_min_length: int = Field(default=8, ge=6, le=128)
    # 连续失败次数达到上限后锁定一段时间
    login_max_failures: int = Field(default=5, ge=1, le=100)
    login_lockout_minutes: int = Field(default=15, ge=1, le=1440)
    # 口令复杂度与历史：必须含字母与数字，且不得与最近 N 次重复；0 表示不查历史
    password_require_mixed: bool = True
    password_history_size: int = Field(default=5, ge=0, le=50)
    # 按来源 IP 的登录尝试窗口（与账号锁定互补）
    login_attempt_window_minutes: int = Field(default=10, ge=1, le=1440)
    login_attempts_per_ip: int = Field(default=20, ge=1, le=1000)
    # 自助重置令牌
    password_reset_ttl_minutes: int = Field(default=30, ge=5, le=1440)
    # 未配置邮件通道时，是否在响应里直接返回重置令牌（仅本地调试，生产必须为 false）
    auth_dev_reveal_reset_token: bool = False
    # 二次验证（TOTP）
    totp_issuer_name: str = "KnowOps"
    totp_window: int = Field(default=1, ge=0, le=5)

    # Captured per uploaded version; existing versions keep their original policy.
    chunk_strategy: Literal["fixed", "structure"] = "fixed"
    chunk_size: int = Field(default=800, ge=200, le=1200)
    chunk_overlap: int = Field(default=100, ge=0, le=199)

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
