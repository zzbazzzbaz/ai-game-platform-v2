import httpx
from langgraph_sdk import Auth

from agent.core.config import get_settings
from agent.core.constants import AUTH_VERIFY_TIMEOUT_SECONDS

auth = Auth()


@auth.authenticate
async def authenticate(authorization: str | None) -> Auth.types.MinimalUserDict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Auth.exceptions.HTTPException(status_code=401, detail="缺少登录 token，请先登录")
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=AUTH_VERIFY_TIMEOUT_SECONDS) as client:
            resp = await client.get(
                f"{settings.internal_verify_url}",
                headers={
                    "Authorization": authorization,
                    "X-Internal-Token": settings.auth_internal_token,
                },
            )
    except httpx.HTTPError as e:
        raise Auth.exceptions.HTTPException(
            status_code=503, detail="鉴权服务不可用，请稍后重试"
        ) from e
    if resp.status_code == 200:
        return {"identity": resp.json()["user_id"]}
    if resp.status_code in (401, 403):
        raise Auth.exceptions.HTTPException(status_code=401, detail="登录已失效，请重新登录")
    raise Auth.exceptions.HTTPException(status_code=503, detail="鉴权服务异常，请稍后重试")
