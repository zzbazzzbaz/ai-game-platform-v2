from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # 模型（provider / model / base_url / api_key 均可配置）
    llm_provider: str
    llm_model_id: str
    llm_base_url: str
    llm_api_key: str

    # 平台内部接口
    api_internal_url: str
    internal_token: str

    # 平台 JWT（本地 JWKS 验签）
    jwks_url: str
    jwt_issuer: str
    jwt_audience: str

    # AGS 沙盒（E2B 协议）
    e2b_domain: str
    e2b_api_key: str

    # LangSmith（可选）
    langsmith_api_key: str
    langsmith_tracing: bool
    langsmith_project: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
