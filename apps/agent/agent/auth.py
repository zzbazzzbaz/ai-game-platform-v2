"""LangGraph 鉴权：平台 JWT 本地验签（RS256 + JWKS 缓存；规格 §8.1 R-AUTH-2）。

- 不引入「由一方代验」的中转接口；公钥按 kid 缓存，日常请求不调外部服务。
"""

import asyncio
from functools import lru_cache

import jwt
from jwt import PyJWKClient
from langgraph_sdk import Auth

from agent.core.config import get_settings

auth = Auth()


@lru_cache
def _jwks_client() -> PyJWKClient:
    settings = get_settings()
    return PyJWKClient(settings.jwks_url, cache_keys=True, lifespan=300)


def _verify(token: str) -> dict:
    settings = get_settings()
    signing_key = _jwks_client().get_signing_key_from_jwt(token)
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "sub"]},
    )
    if payload.get("typ") != "access":
        raise jwt.InvalidTokenError("令牌类型不正确")
    return payload


@auth.authenticate
async def authenticate(authorization: str | None) -> Auth.types.MinimalUserDict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Auth.exceptions.HTTPException(status_code=401, detail="缺少登录 token，请先登录")
    token = authorization[7:].strip()
    try:
        payload = await asyncio.to_thread(_verify, token)
    except jwt.PyJWTError as e:
        raise Auth.exceptions.HTTPException(status_code=401, detail="登录已失效，请重新登录") from e
    except Exception as e:
        raise Auth.exceptions.HTTPException(
            status_code=503, detail="鉴权服务不可用，请稍后重试"
        ) from e
    return {"identity": payload["sub"]}
