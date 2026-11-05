"""游戏 / 会话业务：创建游戏时开通数据库并种入工作区。"""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.gateways.cos import CosGateway
from app.gateways.pg_admin import PgAdminGateway
from app.models.game import Game
from app.models.thread import GameThread
from app.models.version import GameVersion
from app.repositories.game_repository import game_repository
from app.repositories.thread_repository import thread_repository
from app.repositories.version_repository import version_repository


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
    return version_repository.list_by_game(session, game_id)
