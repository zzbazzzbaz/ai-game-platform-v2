"""资源命名派生：一切外部资源名只由 game_id 推导（规格 §5.3）。"""

from app.core.constants import GAME_DB_PREFIX, GAME_DB_ROLE_SUFFIX


def game_sid(game_id: object) -> str:
    """sid = game_id 去掉横线（32 位十六进制）。"""
    return str(game_id).replace("-", "")


def game_database_name(game_id: object) -> str:
    return f"{GAME_DB_PREFIX}{game_sid(game_id)}"


def game_database_role(game_id: object) -> str:
    return f"{game_database_name(game_id)}{GAME_DB_ROLE_SUFFIX}"
