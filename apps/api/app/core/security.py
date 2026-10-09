"""自建认证：RS256 JWT 签发/验签、JWKS、游戏库口令派生（规格 §5.3 / §8）。"""

import base64
import hashlib
import hmac
import json
import time
import uuid
from functools import lru_cache

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.constants import (
    ACCESS_TOKEN_TYPE,
    JWT_ALGORITHM,
    REFRESH_TOKEN_TYPE,
)
from app.core.exceptions import ValidationError


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


@lru_cache
def _private_key() -> str:
    with open(get_settings().jwt_private_key_path, encoding="utf-8") as handle:
        return handle.read()


@lru_cache
def _public_key() -> str:
    with open(get_settings().jwt_public_key_path, encoding="utf-8") as handle:
        return handle.read()


@lru_cache
def _key_id() -> str:
    return hashlib.sha256(_public_key().encode("utf-8")).hexdigest()[:16]


def _encode_token(user_id: str, token_type: str, ttl_seconds: int) -> str:
    settings = get_settings()
    now = int(time.time())
    payload = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": str(user_id),
        "iat": now,
        "exp": now + ttl_seconds,
        "jti": uuid.uuid4().hex,
        "typ": token_type,
    }
    return jwt.encode(payload, _private_key(), algorithm=JWT_ALGORITHM, headers={"kid": _key_id()})


def create_access_token(user_id: str) -> tuple[str, int]:
    """返回 (token, 有效秒数)。"""
    ttl = get_settings().access_token_ttl_seconds
    return _encode_token(user_id, ACCESS_TOKEN_TYPE, ttl), ttl


def create_refresh_token(user_id: str) -> str:
    return _encode_token(user_id, REFRESH_TOKEN_TYPE, get_settings().refresh_token_ttl_seconds)


def decode_token(token: str, *, expected_type: str) -> dict:
    """本地验签并校验 iss/aud/exp；失败抛 ValidationError（由调用方映射 401）。"""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            _public_key(),
            algorithms=[JWT_ALGORITHM],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as e:
        raise ValidationError("令牌无效或已过期") from e
    if payload.get("typ") != expected_type:
        raise ValidationError("令牌类型不正确")
    return payload


def decode_access_token(token: str) -> str:
    """校验 access_token，返回 user_id。"""
    payload = decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise ValidationError("令牌缺少用户标识")
    return user_id


def decode_refresh_token(token: str) -> str:
    payload = decode_token(token, expected_type=REFRESH_TOKEN_TYPE)
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise ValidationError("令牌缺少用户标识")
    return user_id


def jwks() -> dict:
    """平台 JWKS（供 agent 本地验签）。"""
    from cryptography.hazmat.primitives import serialization

    public_key = serialization.load_pem_public_key(_public_key().encode("utf-8"))
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public_key))
    jwk.update({"kid": _key_id(), "use": "sig", "alg": JWT_ALGORITHM})
    return {"keys": [jwk]}


def derive_game_db_password(game_id: str) -> str:
    """base64url(HMAC-SHA256(master_secret, game_id))；不落库、不轮换。"""
    secret = get_settings().game_db_password_master_secret.encode("utf-8")
    digest = hmac.new(secret, str(game_id).encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")
