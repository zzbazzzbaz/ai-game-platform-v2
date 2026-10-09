import httpx
from langchain_core.tools import BaseTool
from langchain_core.tools import tool as make_tool

from agent.core.constants import (
    MOCK_USER_ID,
    PUBLISH_SINGLE_GAME_PATH,
    PUBLISH_TIMEOUT_SECONDS,
)


def make_publish_single_game_tool(
    *,
    thread_id: str,
    api_internal_url: str,
    internal_token: str,
) -> BaseTool:
    """构造 publish_single_game 工具：Agent 只发发布请求，落桶与校验由 api_server 完成。"""

    @make_tool
    def publish_single_game(name: str = "") -> str:
        """把当前游戏发布到平台，返回公网可玩链接。

        发布前必须先在工作区执行 `npm run build` 生成 dist/index.html。
        name 可选，用于给游戏起个名字。
        """
        try:
            response = httpx.post(
                f"{api_internal_url}{PUBLISH_SINGLE_GAME_PATH}",
                headers={"X-Internal-Token": internal_token},
                json={"thread_id": thread_id, "user_id": MOCK_USER_ID, "name": name},
                timeout=PUBLISH_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as e:
            return f"发布失败：无法连接发布服务（{e}）"
        if response.status_code == 200:
            data = response.json()
            return f"发布成功，公网链接：{data['url']}（{data['size']} 字节）"
        try:
            detail = response.json().get("detail") or response.text
        except ValueError:
            detail = response.text
        return f"发布失败（{response.status_code}）：{detail}"

    return publish_single_game
