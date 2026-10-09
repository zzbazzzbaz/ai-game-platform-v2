from langchain_core.tools import BaseTool
from langchain_core.tools import tool as make_tool

from agent.core.constants import INTERNAL_TIMEOUT_SECONDS, PROVISION_DATABASE_PATH
from agent.tools.internal_api import InternalApiError, call_internal


def make_provision_database_tool(*, thread_id: str) -> BaseTool:
    """构造 provision_database 工具：为当前游戏幂等开通独占数据库。"""

    @make_tool
    def provision_database() -> str:
        """为当前游戏开通（或确认）独占数据库，返回连接串。

        平台在创建游戏时已开通并把 DATABASE_URL 注入沙盒环境；仅当环境变量缺失时调用本工具。
        """
        try:
            data = call_internal(
                PROVISION_DATABASE_PATH,
                {"thread_id": thread_id},
                timeout=INTERNAL_TIMEOUT_SECONDS,
            )
        except InternalApiError as e:
            return f"数据库开通失败：{e}"
        return f"数据库已就绪（连接串已注入环境变量 DATABASE_URL）：{data['database_url']}"

    return provision_database
