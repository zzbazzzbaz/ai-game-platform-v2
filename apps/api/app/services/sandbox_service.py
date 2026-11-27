"""沙盒编排：ensure（前缀兜底 → AGS 创建/复用 → 保活游戏服务）/ 预览地址。

初始化全部由镜像 entrypoint 完成（见 sandbox/image/）：
  1. 工作区 /workspace/work 为空时，从镜像模板 /opt/game-template 播种（COS 挂载）
  2. node_modules 软链到镜像内依赖；skills 常驻 /opt/skills
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import (
    GAME_SERVER_ENSURE_COMMAND,
    GAME_SERVER_PORT,
    SANDBOX_RENEW_TIMEOUT_SECONDS,
)
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
    """确保会话所属游戏的沙盒可用。

    并发安全：用 `games` 行锁把同一游戏的 ensure 串行化（见 `game_repository.lock`），
    否则两个并发请求会各自创建一个沙盒，后写的覆盖先写的，多出来的成为孤儿。
    """
    _thread, game = _resolve(thread_id, session)
    game_id = str(game.game_id)

    # 与沙盒无关的准备工作放锁外，尽量缩短行锁持有时间
    cos.ensure_game_prefixes(game.game_id)
    database_url = pg_admin.game_database_url(game_id)

    # 行锁起点：覆盖「读 sandbox_id → 创建/复用沙盒 → 写 sandbox_id」的临界区
    locked = game_repository.lock(session, game_id=game.game_id)
    if locked is None:
        raise NotFoundError("游戏不存在")

    sandbox_id, created = ags.ensure(
        game_id=game_id,
        sandbox_id=locked.sandbox_id,
        envs={"DATABASE_URL": database_url, "PORT": str(GAME_SERVER_PORT)},
    )
    if locked.sandbox_id != sandbox_id:
        game_repository.set_sandbox_id(session, game_id=locked.game_id, sandbox_id=sandbox_id)
    else:
        # 无变更也要提交：提交（或回滚）才会释放行锁
        session.commit()

    # 保活命令最长可跑 180s，必须在锁外执行
    _ensure_server_running(sandbox_id=sandbox_id, ags=ags)
    return {
        "thread_id": thread_id,
        "game_id": locked.game_id,
        "sandbox_id": sandbox_id,
        "created": created,
    }


def renew_sandbox_for_thread(
    *, thread_id: uuid.UUID, session: Session, ags: AgsGateway
) -> dict[str, Any]:
    """前端轮询续期：只续已有沙盒，不创建；失效时返回 renewed=False。"""
    _thread, game = _resolve(thread_id, session)
    sandbox_id = game.sandbox_id
    renewed = False
    if sandbox_id is not None:
        renewed = ags.renew(sandbox_id, timeout_seconds=SANDBOX_RENEW_TIMEOUT_SECONDS)
    return {
        "thread_id": thread_id,
        "sandbox_id": sandbox_id,
        "renewed": renewed,
        "timeout_seconds": SANDBOX_RENEW_TIMEOUT_SECONDS,
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
