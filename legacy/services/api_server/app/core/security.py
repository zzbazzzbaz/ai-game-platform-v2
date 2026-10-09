import base64
import hashlib
import hmac
import json
import secrets
import time

from app.core.config import get_settings
from app.core.constants import USER_ID_PATTERN


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign_token(user_id: str) -> tuple[str, int]:
    settings = get_settings()
    exp = int(time.time()) + settings.auth_token_ttl_seconds
    payload = _b64(json.dumps({"sub": user_id, "exp": exp, "nonce": secrets.token_hex(8)}).encode())
    sig = _b64(hmac.new(settings.auth_secret.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}", settings.auth_token_ttl_seconds


def verify_token(token: str) -> str | None:
    try:
        payload, _, sig = token.partition(".")
        expect = _b64(
            hmac.new(get_settings().auth_secret.encode(), payload.encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig, expect):
            return None
        body = json.loads(_unb64(payload))
        if not isinstance(body, dict):
            return None
        exp = body.get("exp", 0)
        if not isinstance(exp, (int, float)) or exp < time.time():
            return None
        user_id = body.get("sub", "")
        if not isinstance(user_id, str):
            return None
        return user_id if USER_ID_PATTERN.match(user_id) else None
    except ValueError, KeyError:
        return None
