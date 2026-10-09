"""游戏库开通：管理员直连自建 PG，幂等创建 database + role（规格 §6.5）。

- 只动平台自己的库 / role；该实例为共享实例，**禁止**改其它库的 ACL。
- 幂等：存在则跳过，不重建、不改密码（滚动更新期间旧实例凭据必须继续可用）。
- 开通必须 `REVOKE CONNECT ... FROM PUBLIC`，否则任意 role 可连任意库（实测结论）。
"""

import psycopg
from psycopg import sql

from app.core.exceptions import UpstreamError
from app.core.naming import game_database_name, game_database_role
from app.core.security import derive_game_db_password


class PgAdminGateway:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        admin_db: str,
        game_db_host: str,
        game_db_port: int,
        sslmode: str,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._admin_db = admin_db
        self._game_db_host = game_db_host
        self._game_db_port = game_db_port
        self._sslmode = sslmode

    def _connect(self, dbname: str) -> psycopg.Connection:
        return psycopg.connect(
            host=self._host,
            port=self._port,
            dbname=dbname,
            user=self._user,
            password=self._password,
            connect_timeout=10,
            autocommit=True,
        )

    def _database_exists(self, dbname: str) -> bool:
        with self._connect(self._admin_db) as conn:
            row = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)).fetchone()
        return row is not None

    def _role_exists(self, role: str) -> bool:
        with self._connect(self._admin_db) as conn:
            row = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
        return row is not None

    def ensure_game_database(self, game_id: str) -> None:
        """幂等开通：建库 / 建 role / 收 PUBLIC CONNECT / 授权。"""
        dbname = game_database_name(game_id)
        role = game_database_role(game_id)
        password = derive_game_db_password(str(game_id))
        try:
            if not self._database_exists(dbname):
                with self._connect(self._admin_db) as conn:
                    conn.execute(
                        sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname))
                    )
            with self._connect(self._admin_db) as conn:
                if not self._role_exists(role):
                    conn.execute(
                        sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                            sql.Identifier(role), sql.Literal(password)
                        )
                    )
                conn.execute(
                    sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(
                        sql.Identifier(dbname)
                    )
                )
                conn.execute(
                    sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                        sql.Identifier(dbname), sql.Identifier(role)
                    )
                )
            with self._connect(dbname) as conn:
                conn.execute(
                    sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(
                        sql.Identifier(role)
                    )
                )
        except psycopg.Error as e:
            raise UpstreamError(f"游戏数据库开通失败：{e}") from e

    def game_database_url(self, game_id: str) -> str:
        """派生连接串（不落库）。"""
        dbname = game_database_name(game_id)
        role = game_database_role(game_id)
        password = derive_game_db_password(str(game_id))
        return (
            f"postgresql://{role}:{password}"
            f"@{self._game_db_host}:{self._game_db_port}/{dbname}?sslmode={self._sslmode}"
        )
