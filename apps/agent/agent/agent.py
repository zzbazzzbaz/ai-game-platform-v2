import asyncio
from typing import Any

from deepagents import create_deep_agent
from deepagents.middleware.filesystem import FilesystemMiddleware
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agent.core.constants import ENSURE_SESSION_PATH, ENSURE_TIMEOUT_SECONDS, SKILLS_MOUNT_DIR
from agent.infra.ags import connect_sandbox
from agent.infra.ags_backend import AgsBackend
from agent.infra.model import get_llm
from agent.prompts.game import SYSTEM_PROMPT
from agent.tools.game_maps import (
    make_get_game_map_tool,
    make_list_game_maps_tool,
    make_save_game_map_tool,
)
from agent.tools.internal_api import call_internal
from agent.tools.provision_database import make_provision_database_tool
from agent.tools.publish_game import make_publish_game_tool
from agent.tools.publish_status import make_publish_status_tool


def _require_thread_id(config: RunnableConfig) -> str:
    thread_id = (config.get("configurable") or {}).get("thread_id")
    if not thread_id or not isinstance(thread_id, str):
        raise RuntimeError("会话尚未创建，请先创建新会话再开始对话")
    return thread_id


async def build_game_agent(config: RunnableConfig) -> CompiledStateGraph[Any]:
    """按 thread_id 解析 game_id、确保沙盒就绪，再构建 deepagents 图。"""
    thread_id = _require_thread_id(config)
    ensured = await asyncio.to_thread(
        call_internal,
        ENSURE_SESSION_PATH,
        {"thread_id": thread_id},
        timeout=ENSURE_TIMEOUT_SECONDS,
    )
    sandbox = await asyncio.to_thread(connect_sandbox, ensured["sandbox_id"])
    backend = AgsBackend(sandbox=sandbox)
    return create_deep_agent(
        model=get_llm(),
        system_prompt=SYSTEM_PROMPT,
        skills=[SKILLS_MOUNT_DIR],
        tools=[
            make_provision_database_tool(thread_id=thread_id),
            make_publish_game_tool(thread_id=thread_id),
            make_publish_status_tool(thread_id=thread_id),
            make_list_game_maps_tool(thread_id=thread_id),
            make_get_game_map_tool(thread_id=thread_id),
            make_save_game_map_tool(thread_id=thread_id),
        ],
        backend=backend,
        # 同名 FilesystemMiddleware 覆盖默认实例：read_file 的二进制 base64 先写入
        # 沙盒 /blobs/<sha256>，state/checkpoint 只留 deepagents_blob 引用；每次模型
        # 调用时按引用回填图片。这样会话历史不含 base64，模型仍能看图。
        middleware=[FilesystemMiddleware(backend=backend, offload_binary_content=True)],
    )
