from functools import lru_cache
from urllib.parse import urlparse
from uuid import uuid4

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from agent.core.config import get_settings

_SUPPORTED_PROVIDERS = ("deepseek", "openai")

# OpenCode Go 网关要求客户端用 x-opencode-session 标识会话，缺失直接 400；
# 进程内固定一个 id，既能稳定路由与提示缓存，又不会随对话数增长。
_SESSION_ID = uuid4().hex
_OPENCODE_HOSTS = ("opencode.ai",)


def _default_headers(base_url: str) -> dict[str, str]:
    host = (urlparse(base_url).hostname or "").lower()
    if not any(host == h or host.endswith(f".{h}") for h in _OPENCODE_HOSTS):
        return {}
    return {"x-opencode-session": _SESSION_ID}


@lru_cache
def get_llm() -> BaseChatModel:
    settings = get_settings()
    if settings.llm_provider not in _SUPPORTED_PROVIDERS:
        raise ValueError(
            f"不支持的 LLM_PROVIDER：{settings.llm_provider}，仅支持 {'/'.join(_SUPPORTED_PROVIDERS)}"
        )
    kwargs: dict[str, dict[str, str]] = {}
    headers = _default_headers(settings.llm_base_url)
    if headers:
        kwargs["default_headers"] = headers
    return init_chat_model(
        settings.llm_model_id,
        model_provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        **kwargs,
    )
