import asyncio
from collections.abc import Callable

from deepagents import create_deep_agent
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agent.core.config import get_settings
from agent.core.constants import SKILL_MOUNT_DIR
from agent.infra.modal_backend import ModalBackend
from agent.infra.modal_sandbox import attach_thread_sandbox
from agent.infra.model import get_llm
from agent.middleware.auto_snapshot import make_auto_snapshot_middleware
from agent.prompts.single import SYSTEM_PROMPT as SINGLE_PROMPT
from agent.tools.publish_single_game import make_publish_single_game_tool


def _require_thread_id(config: RunnableConfig) -> str:
    thread_id = (config.get("configurable") or {}).get("thread_id")
    if not thread_id or not isinstance(thread_id, str):
        raise RuntimeError("会话尚未创建，请先创建新会话再开始对话")
    return thread_id


async def build_single_agent(config: RunnableConfig) -> CompiledStateGraph:
    thread_id = _require_thread_id(config)
    settings = get_settings()
    sandbox = await asyncio.to_thread(attach_thread_sandbox, thread_id)
    publish_tool: Callable = make_publish_single_game_tool(
        thread_id=thread_id,
        api_internal_url=settings.api_internal_url,
        internal_token=settings.auth_internal_token,
    )
    auto_snapshot = make_auto_snapshot_middleware(
        thread_id=thread_id,
        api_internal_url=settings.api_internal_url,
        internal_token=settings.auth_internal_token,
    )
    return create_deep_agent(
        model=get_llm(),
        system_prompt=SINGLE_PROMPT,
        skills=[SKILL_MOUNT_DIR],
        tools=[publish_tool],
        middleware=[auto_snapshot],
        backend=ModalBackend(sandbox=sandbox),
    )


async def build_multi_agent(config: RunnableConfig) -> CompiledStateGraph:
    raise NotImplementedError("多人模式尚未实现")
