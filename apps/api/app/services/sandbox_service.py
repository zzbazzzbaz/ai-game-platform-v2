"""沙盒编排：ensure（前缀兜底 → AGS 创建/复用 → 保活游戏服务）/ 预览地址。

初始化全部由镜像 entrypoint 完成（见 sandbox/image/）：
  1. 工作区 /workspace/work 为空时，从镜像模板 /opt/game-template 播种（COS 挂载）
  2. node_modules 软链到镜像内依赖；skills 常驻 /opt/skills
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import GAME_SERVER_ENSURE_COMMAND, GAME_SERVER_PORT
from app.core.exceptions import NotFoundError
from app.gateways.ags import AgsGateway
from app.gateways.cos import CosGateway
from app.gateways.pg_admin import PgAdminGateway
from app.models.game import Game
from app.models.thread import GameThread
from app.repositories.game_repository import game_repository
from app.repositories.thread_repository import thread_repository


def _resolve(thread_id: uuid.UUID, session: Session) -> tuple[GameThread, Game]:
    thread = thread_repository.get(session, thread_id)
    if thread is None:
        raise NotFoundError("会话不存在")
    game = game_repository.get(session, thread.game_id)
    if game is None:
        raise NotFoundError("游戏不存在")
    return thread, game


def _ensure_server_running(*, sandbox_id: str, ags: AgsGateway) -> None:
    """确保游戏服务进程在运行。"""
    ags.run(sandbox_id, GAME_SERVER_ENSURE_COMMAND, timeout=180)


def ensure_for_thread(
    *,
    thread_id: uuid.UUID,
    session: Session,
    ags: AgsGateway,
    cos: CosGateway,
    pg_admin: PgAdminGateway,
) -> dict[str, Any]:
    thread, game = _resolve(thread_id, session)
    game_id = str(game.game_id)
    cos.ensure_game_prefixes(game.game_id)
    database_url = pg_admin.game_database_url(game_id)
    sandbox_id, created = ags.ensure(
        game_id=game_id,
        sandbox_id=game.sandbox_id,
        envs={"DATABASE_URL": database_url, "PORT": str(GAME_SERVER_PORT)},
    )
    if game.sandbox_id != sandbox_id:
        game_repository.set_sandbox_id(session, game_id=game.game_id, sandbox_id=sandbox_id)
    _ensure_server_running(sandbox_id=sandbox_id, ags=ags)
    return {
        "thread_id": thread_id,
        "game_id": game.game_id,
        "sandbox_id": sandbox_id,
        "created": created,
    }


def preview_url_for_thread(
    *,
    thread_id: uuid.UUID,
    session: Session,
    ags: AgsGateway,
    cos: CosGateway,
    pg_admin: PgAdminGateway,
) -> dict[str, Any]:
    ensured = ensure_for_thread(
        thread_id=thread_id, session=session, ags=ags, cos=cos, pg_admin=pg_admin
    )
    return {
        "thread_id": thread_id,
        "novnc_url": ags.preview_url(ensured["sandbox_id"]),
    }
