from langchain_core.tools import BaseTool
from langchain_core.tools import tool as make_tool

from agent.core.constants import PUBLISH_GAME_PATH, PUBLISH_START_TIMEOUT_SECONDS
from agent.tools.internal_api import InternalApiError, call_internal


def make_publish_game_tool(*, thread_id: str) -> BaseTool:
    """构造 publish_game 工具：受理异步发布，立即返回版本号。"""

    @make_tool
    def publish_game(name: str = "") -> str:
        """在后台发布当前游戏（仅在用户明确要求发布时调用）。

        立即返回版本号，部署通常需要 3-5 分钟；不要等待完成，也不要自动重复调用。
        name 可选，用于给这版发布写个备注。平台后端操作（需平台管理凭证）。
        """
        try:
            data = call_internal(
                PUBLISH_GAME_PATH,
                {"thread_id": thread_id, "name": name},
                timeout=PUBLISH_START_TIMEOUT_SECONDS,
            )
        except InternalApiError as e:
            if e.status_code == 409:
                return f"发布未开始：{e}"
            return f"发布失败：{e}"
        return (
            f"已开始发布版本 #{data['seq']}。"
            "部署在后台进行，通常需要 3-5 分钟；完成后可在版本面板打开链接，"
            "也可以稍后让我查询发布状态。"
        )

    return publish_game
