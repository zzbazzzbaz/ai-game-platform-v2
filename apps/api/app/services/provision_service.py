"""游戏数据库开通（幂等；连接串派生、不落库）。"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.gateways.pg_admin import PgAdminGateway
from app.repositories.thread_repository import thread_repository


def provision_database_for_thread(
    *, thread_id: uuid.UUID, session: Session, pg_admin: PgAdminGateway
) -> dict[str, Any]:
    thread = thread_repository.get(session, thread_id)
    if thread is None:
        raise NotFoundError("会话不存在")
    game_id = str(thread.game_id)
    pg_admin.ensure_game_database(game_id)
    return {"game_id": thread.game_id, "database_url": pg_admin.game_database_url(game_id)}
