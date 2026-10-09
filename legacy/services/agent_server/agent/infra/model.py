from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from agent.core.config import get_settings


@lru_cache
def get_llm() -> BaseChatModel:
    settings = get_settings()
    if settings.llm_provider not in ("deepseek", "openai"):
        raise ValueError(f"不支持的 LLM_PROVIDER：{settings.llm_provider}，仅支持 deepseek/openai")
    return init_chat_model(
        settings.llm_model_id,
        model_provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )
