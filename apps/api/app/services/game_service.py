"""游戏 / 会话业务：创建游戏时开通数据库并种入工作区。"""

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import (
    DEMO_COPY_EXCLUDED_TOP,
    DEMO_KICKOFF_TEMPLATE,
    DEMO_NAME_SUFFIX,
    DEMO_THREAD_TITLE,
)
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.gateways.cos import CosGateway
from app.gateways.pg_admin import PgAdminGateway
from app.models.game import Game
from app.models.thread import GameThread
from app.models.version import GameVersion
from app.repositories.game_repository import game_repository
from app.repositories.thread_repository import thread_repository
from app.repositories.version_repository import version_repository

logger = logging.getLogger(__name__)


def list_games(*, owner_id: uuid.UUID, session: Session) -> list[Game]:
    return game_repository.list_by_owner(session, owner_id)


def get_owned_game(*, owner_id: uuid.UUID, game_id: uuid.UUID, session: Session) -> Game:
    game = game_repository.get(session, game_id)
    if game is None:
        raise NotFoundError("游戏不存在")
    if game.owner_id != owner_id:
        raise ForbiddenError("无权访问该游戏")
    return game


def get_owned_thread(*, owner_id: uuid.UUID, thread_id: uuid.UUID, session: Session) -> GameThread:
    thread = thread_repository.get(session, thread_id)
    if thread is None:
        raise NotFoundError("会话不存在")
    game = game_repository.get(session, thread.game_id)
    if game is None or game.owner_id != owner_id:
        raise ForbiddenError("无权访问该会话")
    return thread


def create_game(
    *,
    owner_id: uuid.UUID,
    name: str,
    session: Session,
    cos: CosGateway,
    pg_admin: PgAdminGateway,
) -> Game:
    """新建游戏：建记录 + 初始会话；数据库开通与工作区前缀占位为幂等副作用。"""
    resolved_name = name.strip() or "未命名游戏"
    game = game_repository.create(session, owner_id=owner_id, name=resolved_name)
    thread_repository.create(session, game_id=game.game_id, title="初始会话")
    cos.ensure_game_prefixes(game.game_id)
    pg_admin.ensure_game_database(str(game.game_id))
    return game


def list_threads(*, owner_id: uuid.UUID, game_id: uuid.UUID, session: Session) -> list[GameThread]:
    get_owned_game(owner_id=owner_id, game_id=game_id, session=session)
    return thread_repository.list_by_game(session, game_id)


def create_thread(
    *, owner_id: uuid.UUID, game_id: uuid.UUID, title: str, session: Session
) -> GameThread:
    get_owned_game(owner_id=owner_id, game_id=game_id, session=session)
    return thread_repository.create(session, game_id=game_id, title=title.strip())


def rename_thread(
    *,
    owner_id: uuid.UUID,
    game_id: uuid.UUID,
    thread_id: uuid.UUID,
    title: str,
    session: Session,
) -> GameThread:
    thread = get_owned_thread(owner_id=owner_id, thread_id=thread_id, session=session)
    if thread.game_id != game_id:
        # 路径里的 game 与会话归属对不上：按不存在处理，不泄露他人会话的存在性
        raise NotFoundError("会话不存在")
    cleaned = title.strip()
    if not cleaned:
        raise ValidationError("标题不能为空")
    renamed = thread_repository.rename(session, thread_id=thread.thread_id, title=cleaned)
    if renamed is None:  # 并发删除的极端竞态
        raise NotFoundError("会话不存在")
    return renamed


def list_versions(
    *, owner_id: uuid.UUID, game_id: uuid.UUID, session: Session
) -> list[GameVersion]:
    get_owned_game(owner_id=owner_id, game_id=game_id, session=session)
    version_repository.reap_stale(session, game_id=game_id)
    return version_repository.list_by_game(session, game_id)


def _demo_kickoff_prompt(*, parent: Game, demo_name: str) -> str:
    if parent.public_url:
        cta = f"完整版地址：{parent.public_url}"
    else:
        cta = "完整版尚未发布：按钮写「完整版即将上线」，不要编造链接。"
    return DEMO_KICKOFF_TEMPLATE.format(
        parent_name=parent.name,
        demo_name=demo_name,
        cta=cta,
    )


def create_demo_game(
    *,
    owner_id: uuid.UUID,
    game_id: uuid.UUID,
    session: Session,
    cos: CosGateway,
    pg_admin: PgAdminGateway,
) -> dict[str, Any]:
    """从当前游戏复制一份独立项目：新 game / 新会话 / 新空库 / COS 工作区。

    复制的是可发布的工作区（与发布链路同一套排除规则），不复制沙盒、聊天历史、
    版本历史、公网地址和数据库数据；新项目第一次发布从 v1 开始。
    """
    parent = get_owned_game(owner_id=owner_id, game_id=game_id, session=session)
    parent_prefix = cos.game_prefix(parent.game_id)
    if not cos.exists(f"{parent_prefix}package.json"):
        raise ValidationError("当前项目还没有游戏代码，请先在对话中生成游戏")

    demo_id = uuid.uuid4()
    demo_prefix = cos.game_prefix(demo_id)
    demo_name = f"{parent.name}{DEMO_NAME_SUFFIX}"

    cos.ensure_game_prefixes(demo_id)
    try:
        cos.copy_prefix(
            source_prefix=parent_prefix,
            dest_prefix=demo_prefix,
            exclude_top=DEMO_COPY_EXCLUDED_TOP,
        )
        pg_admin.ensure_game_database(str(demo_id))
        demo = game_repository.create(
            session, owner_id=owner_id, name=demo_name, game_id=demo_id
        )
        thread = thread_repository.create(
            session, game_id=demo.game_id, title=DEMO_THREAD_TITLE
        )
    except Exception:
        # 复制/开通失败时清掉已写入的工作区，避免留下半成品项目。
        try:
            cos.delete_prefix(demo_prefix)
        except Exception:
            logger.exception("清理体验版工作区失败：game_id=%s", demo_id)
        raise

    return {
        "game_id": demo.game_id,
        "thread_id": thread.thread_id,
        "kickoff_prompt": _demo_kickoff_prompt(parent=parent, demo_name=demo_name),
    }
