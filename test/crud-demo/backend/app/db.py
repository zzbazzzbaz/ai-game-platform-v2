import os

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

# 数据库连接串。默认指向 docker-compose 起的本地 Postgres。
# 真实项目里由环境变量/DATABASE_URL 注入（绝不硬编码）。
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:5432/crud_demo",
)

# 连接池：进程内复用连接，避免每个请求都新建连接。
# row_factory=dict_row 让查询结果直接是 dict（方便转 JSON）。
# check=... 表示"每次取出连接先探活"，数据库重启后首个请求也不会失败。
pool = ConnectionPool(
    DATABASE_URL,
    min_size=1,
    max_size=5,
    kwargs={"row_factory": dict_row},
    check=ConnectionPool.check_connection,
    open=False,
)
