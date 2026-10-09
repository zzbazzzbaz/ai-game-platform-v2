import logging

import httpx
from langchain.agents.middleware import AgentMiddleware, after_agent

from agent.core.constants import AUTO_SNAPSHOT_PATH, AUTO_SNAPSHOT_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


def make_auto_snapshot_middleware(
    *, thread_id: str, api_internal_url: str, internal_token: str
) -> AgentMiddleware:
    """run 正常结束后触发一次工作区快照（best-effort，失败不影响 run）。"""

    @after_agent(name="AutoSnapshotMiddleware")
    async def auto_snapshot_after_agent(state, runtime) -> None:
        try:
            async with httpx.AsyncClient(timeout=AUTO_SNAPSHOT_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{api_internal_url}{AUTO_SNAPSHOT_PATH}/{thread_id}/snapshot",
                    headers={"X-Internal-Token": internal_token},
                )
        except Exception as e:
            logger.warning("自动快照失败 thread=%s：%s", thread_id, e)
        else:
            if response.status_code != 200:
                logger.warning(
                    "自动快照失败 thread=%s：HTTP %s %s",
                    thread_id,
                    response.status_code,
                    response.text,
                )
        return None

    return auto_snapshot_after_agent
