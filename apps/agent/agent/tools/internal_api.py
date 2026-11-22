"""内部接口调用（agent → api；契约权威：apps/api/app/api/schemas/internal.py）。"""

from typing import Any

import httpx

from agent.core.config import get_settings
from agent.core.constants import INTERNAL_TOKEN_HEADER


class InternalApiError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def call_internal(
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: int,
    method: str = "POST",
) -> dict[str, Any]:
    settings = get_settings()
    url = f"{settings.api_internal_url.rstrip('/')}{path}"
    try:
        response = httpx.request(
            method,
            url,
            headers={INTERNAL_TOKEN_HEADER: settings.internal_token},
            json=payload if method != "GET" else None,
            timeout=timeout,
        )
    except httpx.HTTPError as e:
        raise InternalApiError(f"无法连接平台服务（{e}）") from e
    if not response.is_success:
        try:
            detail = response.json().get("detail") or response.text
        except ValueError:
            detail = response.text
        raise InternalApiError(
            f"平台服务返回 {response.status_code}：{detail}",
            status_code=response.status_code,
        )
    data: dict[str, Any] = response.json()
    return data
