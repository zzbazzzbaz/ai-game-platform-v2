"""注册 / 登录 / 刷新（无状态 JWT；口令 bcrypt）。"""

from sqlalchemy.orm import Session

from app.core.constants import MAX_PASSWORD_BYTES, MIN_PASSWORD_LENGTH, STATUS_ACTIVE
from app.core.exceptions import ForbiddenError, ValidationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.repositories.user_repository import user_repository


def _validate_username(username: str) -> str:
    resolved = username.strip()
    if not (3 <= len(resolved) <= 64):
        raise ValidationError("用户名长度须为 3-64 个字符")
    return resolved


def _validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"密码长度至少 {MIN_PASSWORD_LENGTH} 位")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValidationError("密码过长（UTF-8 编码不超过 72 字节）")


def _issue_tokens(user_id: str) -> dict:
    access_token, expires_in = create_access_token(user_id)
    return {
        "access_token": access_token,
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
        "expires_in": expires_in,
    }


def register(*, username: str, password: str, session: Session) -> dict:
    resolved = _validate_username(username)
    _validate_password(password)
    if user_repository.get_by_username(session, resolved) is not None:
        raise ValidationError("用户名已被占用")
    user = user_repository.create(
        session, username=resolved, password_hash=hash_password(password)
    )
    return {
        "user_id": user.user_id,
        "username": user.username,
        **_issue_tokens(str(user.user_id)),
    }


def login(*, username: str, password: str, session: Session) -> dict:
    user = user_repository.get_by_username(session, username.strip())
    if user is None or not verify_password(password, user.password_hash):
        raise ValidationError("用户名或密码错误")
    if user.status != STATUS_ACTIVE:
        raise ForbiddenError("账号已被禁用")
    return {
        "user_id": user.user_id,
        "username": user.username,
        **_issue_tokens(str(user.user_id)),
    }


def refresh(*, refresh_token: str, session: Session) -> dict:
    user_id = decode_refresh_token(refresh_token)
    user = user_repository.get(session, user_id)
    if user is None:
        raise ValidationError("账号不存在")
    if user.status != STATUS_ACTIVE:
        raise ForbiddenError("账号已被禁用")
    return {
        "user_id": user.user_id,
        "username": user.username,
        **_issue_tokens(str(user.user_id)),
    }
