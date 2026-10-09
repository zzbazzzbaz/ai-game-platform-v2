from langchain_core.tools import BaseTool
from langchain_core.tools import tool as make_tool

from agent.core.constants import INTERNAL_TIMEOUT_SECONDS, RESTART_SERVER_PATH
from agent.tools.internal_api import InternalApiError, call_internal


def make_restart_server_tool(*, thread_id: str) -> BaseTool:
    """构造 restart_server 工具：重启沙盒内游戏服务并返回日志尾部。"""

    @make_tool
    def restart_server() -> str:
        """重启沙盒内的游戏服务进程，返回启动日志（改完服务端代码后可调用）。"""
        try:
            data = call_internal(
                RESTART_SERVER_PATH.format(thread_id=thread_id),
                {},
                timeout=INTERNAL_TIMEOUT_SECONDS,
            )
        except InternalApiError as e:
            return f"重启失败：{e}"
        status = "成功" if data.get("ok") else "异常退出"
        return f"游戏服务重启{status}，日志尾部：\n{data.get('log_tail', '')}"

    return restart_server
