"""AGS 沙盒连接（创建 / 生命周期由 api 负责；agent 只连接既有实例）。"""

from e2b import Sandbox

from agent.core.config import get_settings


def connect_sandbox(sandbox_id: str) -> Sandbox:
    settings = get_settings()
    return Sandbox.connect(
        sandbox_id, api_key=settings.e2b_api_key, domain=settings.e2b_domain
    )
