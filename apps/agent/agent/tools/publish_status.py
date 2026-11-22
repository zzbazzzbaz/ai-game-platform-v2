from langchain_core.tools import BaseTool
from langchain_core.tools import tool as make_tool

from agent.core.constants import PUBLISH_STATUS_PATH, PUBLISH_STATUS_TIMEOUT_SECONDS
from agent.tools.internal_api import InternalApiError, call_internal


def make_publish_status_tool(*, thread_id: str) -> BaseTool:
    """构造 publish_status 工具：查询本游戏最近一次发布的状态。"""

    @make_tool
    def publish_status() -> str:
        """查询本游戏最近一次发布的状态（发布中/已上线/失败/尚未发布）。

        只读且立即返回，不会等待部署完成；用户问发布进度或发布后需要确认时调用。
        """
        try:
            data = call_internal(
                f"{PUBLISH_STATUS_PATH}?thread_id={thread_id}",
                timeout=PUBLISH_STATUS_TIMEOUT_SECONDS,
                method="GET",
            )
        except InternalApiError as e:
            return f"查询发布状态失败：{e}"

        version = data.get("version")
        if not version:
            return "这个游戏还没有发布过。"

        seq = version["seq"]
        status = version["status"]
        if status == "deploying":
            return f"版本 #{seq} 正在发布中，通常还需几分钟；完成后会生成公网链接。"
        if status == "failed":
            return f"版本 #{seq} 发布失败。确认预览正常后可以重新发布。"
        public_url = data.get("public_url")
        if public_url:
            return f"版本 #{seq} 已上线，公网链接：{public_url}"
        return f"版本 #{seq} 已上线。"

    return publish_status
