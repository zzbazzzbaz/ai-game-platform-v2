"""内部接口调用（agent → api；契约权威：apps/api/app/api/schemas/internal.py）。"""

import httpx

from agent.core.config import get_settings
from agent.core.constants import INTERNAL_TOKEN_HEADER


class InternalApiError(Exception):
    pass


def call_internal(path: str, payload: dict, *, timeout: int) -> dict:
    settings = get_settings()
    url = f"{settings.api_internal_url.rstrip('/')}{path}"
    try:
        response = httpx.post(
            url,
            headers={INTERNAL_TOKEN_HEADER: settings.internal_token},
            json=payload,
            timeout=timeout,
        )
    except httpx.HTTPError as e:
        raise InternalApiError(f"无法连接平台服务（{e}）") from e
    if response.status_code != 200:
        try:
            detail = response.json().get("detail") or response.text
        except ValueError:
            detail = response.text
        raise InternalApiError(f"平台服务返回 {response.status_code}：{detail}")
    return response.json()
