"""pytest 公共夹具。

- 测试跑在独立的 PG 库（`aigame_platform_test`）上，库在测试会话开始/结束时自动建/删；
- 沙盒与外部服务全部替换为假实现（`tests/fakes.py`），测试不触达 AGS / COS / 游戏库；
- 配置复用 `apps/.env`，只覆盖数据库地址与内部令牌。
"""

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

import app.gateways.ags as ags_module
import app.models  # noqa: F401  确保建表模型已注册
from app.core.config import Settings
from app.core.constants import INTERNAL_TOKEN_HEADER, PLATFORM_SCHEMA
from app.core.database import create_all, create_db_engine, create_session_factory
from app.models.game import Game
from app.models.thread import GameThread
from app.models.user import User
from tests.fakes import FakeSandbox

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
TEST_DATABASE_NAME = "aigame_platform_test"
TEST_INTERNAL_TOKEN = "test-internal-token"


def read_env_file() -> dict[str, str]:
    """把 apps/.env 读成 dict（与 Makefile 的 --env-file 同源）。"""
    values: dict[str, str] = {}
    for raw in ENV_FILE.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


# `app.main` 在 import 时就会 `create_app()`（读环境变量），因此要在导入应用前把
# apps/.env 注入 os.environ（不覆盖真实环境变量）。
for _key, _value in read_env_file().items():
    os.environ.setdefault(_key, _value)


@pytest.fixture(scope="session")
def settings() -> Settings:
    """应用配置：复用 apps/.env，但数据库/内部令牌强制指向测试环境。

    两个坑（都踩过）：
    1. pydantic-settings 里环境变量优先级**高于**传参，`model_validate(values)` /
       `Settings(**values)` 都压不住 os.environ 里的同名变量（app.main 需要 env），
       因此必须构造后显式赋值；
    2. `str(URL)` 会按 `hide_password=True` 渲染，把口令变成 `***`，
       构造连接串要用 `render_as_string(hide_password=False)`。
    """
    values = read_env_file()
    dev_url = make_url(values["PLATFORM_DATABASE_URL"])
    assert dev_url.database != TEST_DATABASE_NAME, "开发库地址不能就是测试库"

    test_dsn = dev_url.set(database=TEST_DATABASE_NAME).render_as_string(hide_password=False)
    resolved = Settings.model_validate(values)
    resolved.platform_database_url = test_dsn
    resolved.internal_token = TEST_INTERNAL_TOKEN

    resolved_url = make_url(resolved.sqlalchemy_database_url)
    assert resolved_url.database == TEST_DATABASE_NAME, (
        f"测试配置必须指向独立测试库，实际为 {resolved_url.database!r}"
    )
    assert resolved_url.password == dev_url.password, "测试库连接串必须沿用原口令（别被隐码成 ***）"
    return resolved


def assert_is_test_database(url: str) -> None:
    """护栏：任何测试用库都必须是独立测试库，防止误连开发库（会清空真实数据）。"""
    database = make_url(url).database
    assert database == TEST_DATABASE_NAME, (
        f"拒绝在非测试库上执行测试操作：{database!r} != {TEST_DATABASE_NAME!r}"
    )


@pytest.fixture(scope="session")
def test_database_url(settings: Settings) -> Iterator[str]:
    """建独立测试库（同名库先删后建），测试会话结束后删除。"""
    dev_url = make_url(read_env_file()["PLATFORM_DATABASE_URL"])
    assert dev_url.database != TEST_DATABASE_NAME, "开发库地址不能就是测试库"
    admin_engine = create_engine(dev_url.set(database="postgres"), isolation_level="AUTOCOMMIT")

    def recreate() -> None:
        with admin_engine.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DATABASE_NAME}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{TEST_DATABASE_NAME}"'))

    recreate()
    try:
        yield settings.sqlalchemy_database_url
    finally:
        with admin_engine.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DATABASE_NAME}" WITH (FORCE)'))
        admin_engine.dispose()


@pytest.fixture(scope="session")
def db_engine(test_database_url: str) -> Iterator[Engine]:
    """测试库引擎 + 建表（与 api 启动流程一致：先建 schema 再 create_all）。"""
    assert_is_test_database(test_database_url)
    engine = create_db_engine(test_database_url)
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{PLATFORM_SCHEMA}"'))
    create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def session_factory(db_engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(db_engine)


@pytest.fixture(autouse=True)
def _clean_tables(db_engine: Engine) -> Iterator[None]:
    """每个用例前清空平台表（只允许在测试库上执行）。"""
    assert_is_test_database(str(db_engine.url))
    with db_engine.begin() as conn:
        conn.execute(
            text(
                f'TRUNCATE "{PLATFORM_SCHEMA}".game_maps, '
                f'"{PLATFORM_SCHEMA}".game_threads, "{PLATFORM_SCHEMA}".games, '
                f'"{PLATFORM_SCHEMA}".users CASCADE'
            )
        )
    yield


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session


@pytest.fixture
def user(session: Session) -> User:
    user = User(username=f"tester-{uuid.uuid4().hex[:8]}", password_hash="x")
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def game(session: Session, user: User) -> Game:
    game = Game(owner_id=user.user_id, name="测试游戏")
    session.add(game)
    session.commit()
    return game


@pytest.fixture
def thread(session: Session, game: Game) -> GameThread:
    thread = GameThread(game_id=game.game_id, title="初始会话")
    session.add(thread)
    session.commit()
    return thread


@pytest.fixture
def fake_sandbox(monkeypatch: pytest.MonkeyPatch) -> type[FakeSandbox]:
    """把 app.gateways.ags 里的 Sandbox 换成 FakeSandbox，并清空其状态。"""
    monkeypatch.setattr(ags_module, "Sandbox", FakeSandbox)
    FakeSandbox.reset()
    return FakeSandbox


@pytest.fixture
def internal_headers() -> dict[str, str]:
    return {INTERNAL_TOKEN_HEADER: TEST_INTERNAL_TOKEN}
