"""沙盒编排：ensure（前缀兜底 → AGS 创建/复用 → 初始化）/ 重启游戏服务 / 预览地址。

初始化（`infra/sandbox/init.sh`，由 COS 平台前缀下发）：
  1. skills 解包到 `/opt/skills`（deepagents 经沙盒 backend 读取）
  2. 依赖装到 `/opt/deps`（不进 COS 挂载层）
  3. 软链 `/workspace/work/node_modules → /opt/deps/node_modules`
"""

import uuid

from sqlalchemy.orm import Session

from app.core.constants import (
    COS_INIT_SCRIPT,
    COS_SKILLS_ARCHIVE,
    GAME_SERVER_ENSURE_COMMAND,
    GAME_SERVER_PORT,
    GAME_SERVER_RESTART_COMMAND,
    SANDBOX_INIT_MARKER,
    SANDBOX_SKILLS_TMP,
)
from app.core.exceptions import NotFoundError, UpstreamError, ValidationError
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


def _ensure_init(*, sandbox_id: str, ags: AgsGateway, cos: CosGateway) -> None:
    code, _, _ = ags.run(sandbox_id, f"test -f {SANDBOX_INIT_MARKER}", timeout=30)
    if code == 0:
        return
    skills = cos.get_bytes(cos.platform_key(COS_SKILLS_ARCHIVE))
    if skills is not None:
        ags.write_file(sandbox_id, SANDBOX_SKILLS_TMP, skills)
    script = cos.get_bytes(cos.platform_key(COS_INIT_SCRIPT))
    if script is None:
        raise UpstreamError("沙盒初始化脚本缺失：请先执行 `make sandbox-assets-publish`")
    code, out, err = ags.run(sandbox_id, script.decode("utf-8"), timeout=600)
    if code != 0:
        raise UpstreamError(f"沙盒初始化失败：{(err or out)[-500:]}")


def _ensure_server_running(*, sandbox_id: str, ags: AgsGateway) -> None:
    """确保游戏服务进程在运行（规格 §6.2 生命周期）。"""
    ags.run(sandbox_id, GAME_SERVER_ENSURE_COMMAND, timeout=180)


def ensure_for_thread(
    *,
    thread_id: uuid.UUID,
    session: Session,
    ags: AgsGateway,
    cos: CosGateway,
    pg_admin: PgAdminGateway,
) -> dict:
    thread, game = _resolve(thread_id, session)
    game_id = str(game.game_id)
    cos.ensure_game_prefixes(game.game_id)
    cos.seed_workspace(game.game_id)
    database_url = pg_admin.game_database_url(game_id)
    sandbox_id, created = ags.ensure(
        game_id=game_id,
        sandbox_id=game.sandbox_id,
        envs={"DATABASE_URL": database_url, "PORT": str(GAME_SERVER_PORT)},
    )
    if game.sandbox_id != sandbox_id:
        game_repository.set_sandbox_id(session, game_id=game.game_id, sandbox_id=sandbox_id)
    _ensure_init(sandbox_id=sandbox_id, ags=ags, cos=cos)
    _ensure_server_running(sandbox_id=sandbox_id, ags=ags)
    return {
        "thread_id": thread_id,
        "game_id": game.game_id,
        "sandbox_id": sandbox_id,
        "created": created,
    }


def restart_server(*, thread_id: uuid.UUID, session: Session, ags: AgsGateway) -> dict:
    _, game = _resolve(thread_id, session)
    if not game.sandbox_id:
        raise ValidationError("沙盒尚未创建，请先进入会话")
    code, out, err = ags.run(game.sandbox_id, GAME_SERVER_RESTART_COMMAND, timeout=120)
    return {"ok": code == 0, "log_tail": (out or err)[-2000:]}


def preview_url_for_thread(
    *,
    thread_id: uuid.UUID,
    session: Session,
    ags: AgsGateway,
    cos: CosGateway,
    pg_admin: PgAdminGateway,
) -> dict:
    ensured = ensure_for_thread(
        thread_id=thread_id, session=session, ags=ags, cos=cos, pg_admin=pg_admin
    )
    return {
        "thread_id": thread_id,
        "novnc_url": ags.preview_url(ensured["sandbox_id"]),
    }
