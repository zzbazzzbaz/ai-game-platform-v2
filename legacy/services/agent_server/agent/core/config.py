from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    llm_provider: Literal["deepseek", "openai"]
    llm_model_id: str
    llm_base_url: str
    llm_api_key: str
    modal_token_id: str
    modal_token_secret: str
    modal_app: str
    langsmith_api_key: str
    langsmith_tracing: bool
    langsmith_project: str
    api_internal_url: str
    auth_internal_token: str

    @property
    def internal_verify_url(self) -> str:
        return f"{self.api_internal_url}/api/v1/internal/verify"


@lru_cache
def get_settings() -> Settings:
    return Settings()
