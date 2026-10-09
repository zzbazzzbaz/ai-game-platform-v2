from langchain_core.tools import BaseTool
from langchain_core.tools import tool as make_tool

from agent.core.constants import (
    INTERNAL_TIMEOUT_SECONDS,
    PUBLISH_GAME_PATH,
)
from agent.tools.internal_api import InternalApiError, call_internal


def make_publish_game_tool(*, thread_id: str) -> BaseTool:
    """构造 publish_game 工具：校验并发布当前游戏，返回公网链接。"""

    @make_tool
    def publish_game(name: str = "") -> str:
        """把当前游戏发布到公网，返回可分享链接。

        发布前必须保证工作区能构建（`npm run build`）且游戏服务可运行。
        name 可选，用于给游戏起个名字。
        """
        try:
            data = call_internal(
                PUBLISH_GAME_PATH,
                {"thread_id": thread_id, "name": name},
                timeout=INTERNAL_TIMEOUT_SECONDS,
            )
        except InternalApiError as e:
            return f"发布失败：{e}"
        return f"发布成功，公网链接：{data['public_url']}（版本 #{data['seq']}）"

    return publish_game
