import modal
from modal.exception import NotFoundError

from agent.core.config import get_settings
from agent.core.constants import SANDBOX_NAME_PREFIX, SANDBOX_TAG_THREAD


def sandbox_name(thread_id: str) -> str:
    return f"{SANDBOX_NAME_PREFIX}{thread_id}"


def sandbox_tags(thread_id: str) -> dict[str, str]:
    return {SANDBOX_TAG_THREAD: thread_id}


def attach_thread_sandbox(thread_id: str) -> modal.Sandbox:
    try:
        return modal.Sandbox.from_name(get_settings().modal_app, sandbox_name(thread_id))
    except NotFoundError:
        raise RuntimeError("会话环境已过期，请重新创建会话后再继续") from None
