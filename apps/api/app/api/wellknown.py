from fastapi import APIRouter

from app.core import security

router = APIRouter(tags=["wellknown"])


@router.get("/.well-known/jwks.json")
def jwks() -> dict:
    """平台 JWT 公钥（供 agent 本地验签）。"""
    return security.jwks()
