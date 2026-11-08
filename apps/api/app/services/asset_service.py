"""资源上传：预签名直传 COS，落点即沙盒只读挂载 /workspace/input。

一期不落库：presign 生成 asset_id 与 key；complete 用 HEAD 复核；
list 直接列举 COS；删除按 asset_id 目录批量清理。
"""

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import (
    ASSET_ALLOWED_CONTENT_TYPE_PREFIXES,
    ASSET_ALLOWED_CONTENT_TYPES,
    ASSET_DENIED_EXTENSIONS,
    ASSET_FILENAME_FALLBACK,
    ASSET_FILENAME_MAX_BYTES,
    ASSET_UNSAFE_FILENAME_CHARS,
    SANDBOX_INPUT_ROOT,
)
from app.core.exceptions import ConflictError, ValidationError
from app.gateways.cos import CosGateway
from app.services.game_service import get_owned_game


def _safe_filename(raw: str) -> str:
    """只取 basename，替换危险字符，按 UTF-8 截断到上限。"""
    name = raw.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = "".join(
        "_" if ch in ASSET_UNSAFE_FILENAME_CHARS or ord(ch) < 32 else ch for ch in name
    ).strip()
    cleaned = cleaned.strip(".").strip()
    encoded = cleaned.encode("utf-8")
    if len(encoded) > ASSET_FILENAME_MAX_BYTES:
        cleaned = encoded[:ASSET_FILENAME_MAX_BYTES].decode("utf-8", errors="ignore")
    return cleaned or ASSET_FILENAME_FALLBACK


def _normalize_content_type(raw: str) -> str:
    return raw.split(";", 1)[0].strip().lower()


def _validate_content_type(content_type: str) -> None:
    if content_type in ASSET_ALLOWED_CONTENT_TYPES:
        return
    if any(content_type.startswith(prefix) for prefix in ASSET_ALLOWED_CONTENT_TYPE_PREFIXES):
        return
    raise ValidationError(f"不支持的文件类型：{content_type}")


def _validate_filename(filename: str) -> None:
    extension = os.path.splitext(filename)[1].lower()
    if extension in ASSET_DENIED_EXTENSIONS:
        raise ValidationError(f"不允许上传该类型的文件：{extension}")


def _sandbox_path(asset_id: uuid.UUID, filename: str) -> str:
    return f"{SANDBOX_INPUT_ROOT}/{asset_id}/{filename}"


def _parse_last_modified(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def presign_asset(
    *,
    owner_id: uuid.UUID,
    game_id: uuid.UUID,
    filename: str,
    content_type: str,
    size: int,
    max_bytes: int,
    expires_seconds: int,
    session: Session,
    cos: CosGateway,
) -> dict[str, Any]:
    game = get_owned_game(owner_id=owner_id, game_id=game_id, session=session)
    safe_name = _safe_filename(filename)
    _validate_filename(safe_name)
    normalized_type = _normalize_content_type(content_type)
    _validate_content_type(normalized_type)
    if size > max_bytes:
        raise ValidationError(f"文件超过大小限制（最大 {max_bytes} 字节）")

    asset_id = uuid.uuid4()
    key = cos.input_key(game.game_id, asset_id, safe_name)
    upload_url = cos.presign_put(
        key, content_type=normalized_type, expires_seconds=expires_seconds
    )
    return {
        "asset_id": asset_id,
        "filename": safe_name,
        "key": key,
        "upload_url": upload_url,
        "method": "PUT",
        "headers": {"Content-Type": normalized_type},
        "expires_at": datetime.now(UTC) + timedelta(seconds=expires_seconds),
        "sandbox_path": _sandbox_path(asset_id, safe_name),
    }


def complete_asset(
    *,
    owner_id: uuid.UUID,
    game_id: uuid.UUID,
    asset_id: uuid.UUID,
    filename: str,
    max_bytes: int,
    session: Session,
    cos: CosGateway,
) -> dict[str, Any]:
    game = get_owned_game(owner_id=owner_id, game_id=game_id, session=session)
    safe_name = _safe_filename(filename)
    key = cos.input_key(game.game_id, asset_id, safe_name)
    head = cos.head_object(key)
    if head is None:
        raise ConflictError("上传未完成或文件不存在")

    try:
        size = int(str(head.get("Content-Length", "0")))
    except ValueError:
        size = 0
    if size <= 0:
        cos.delete_object(key)
        raise ValidationError("文件为空，已清理")
    if size > max_bytes:
        cos.delete_object(key)
        raise ValidationError(f"文件超过大小限制（最大 {max_bytes} 字节），已清理")

    content_type = _normalize_content_type(str(head.get("Content-Type", "")))
    _validate_content_type(content_type)
    return {
        "asset_id": asset_id,
        "filename": safe_name,
        "key": key,
        "size": size,
        "content_type": content_type,
        "sandbox_path": _sandbox_path(asset_id, safe_name),
    }


def list_assets(
    *, owner_id: uuid.UUID, game_id: uuid.UUID, session: Session, cos: CosGateway
) -> list[dict[str, Any]]:
    game = get_owned_game(owner_id=owner_id, game_id=game_id, session=session)
    prefix = cos.input_prefix(game.game_id)
    items: list[dict[str, Any]] = []
    for item in cos.list_objects(prefix):
        key = str(item.get("Key", ""))
        relative = key[len(prefix) :]
        if not relative or relative == ".keep" or relative.endswith("/"):
            continue
        parts = relative.split("/", 1)
        if len(parts) != 2 or not parts[1]:
            continue
        try:
            asset_id = uuid.UUID(parts[0])
        except ValueError:
            continue
        try:
            size = int(str(item.get("Size", "0")))
        except ValueError:
            size = 0
        items.append(
            {
                "asset_id": asset_id,
                "filename": parts[1],
                "key": key,
                "size": size,
                "last_modified": _parse_last_modified(item.get("LastModified")),
                "sandbox_path": _sandbox_path(asset_id, parts[1]),
            }
        )
    return items


def delete_asset(
    *, owner_id: uuid.UUID, game_id: uuid.UUID, asset_id: uuid.UUID, session: Session, cos: CosGateway
) -> None:
    game = get_owned_game(owner_id=owner_id, game_id=game_id, session=session)
    cos.delete_prefix(f"{cos.input_prefix(game.game_id)}{asset_id}/")
