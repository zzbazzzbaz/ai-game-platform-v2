"""`ensure_for_thread` 行为与并发去重。

核心回归：两个并发请求（旧沙盒已被回收）**只能创建一个沙盒**——
对应 2026-10-12 早上「同一个游戏出现两个沙盒」的事故。
"""

import threading
import uuid
from typing import Any

from sqlalchemy import Connection, event
from sqlalchemy.orm import Session, sessionmaker

from app.gateways.ags import AgsGateway
from app.models.game import Game
from app.models.thread import GameThread
from app.repositories.game_repository import game_repository
from app.services import sandbox_service
from tests.fakes import (
    FakeCos,
    FakePgAdmin,
    FakeSandbox,
    read_game_sandbox,
    set_game_sandbox,
)

TIMEOUT_SECONDS = 3600
TEMPLATE = "sdt-test"


def _gateway() -> AgsGateway:
    """真实 AgsGateway + 被替换的 Sandbox（不触网）。"""
    return AgsGateway(
        domain="test.ags.local",
        api_key="test-key",
        template=TEMPLATE,
        timeout_seconds=TIMEOUT_SECONDS,
    )


def _ensure(
    *,
    session: Session,
    thread_id: uuid.UUID,
    cos: FakeCos | None = None,
    pg_admin: FakePgAdmin | None = None,
) -> dict[str, Any]:
    return sandbox_service.ensure_for_thread(
        thread_id=thread_id,
        session=session,
        ags=_gateway(),
        cos=cos if cos is not None else FakeCos(),
        pg_admin=pg_admin if pg_admin is not None else FakePgAdmin(),
    )


def test_reuse_alive_sandbox(
    session: Session,
    session_factory: sessionmaker[Session],
    thread: GameThread,
    fake_sandbox: type[FakeSandbox],
) -> None:
    """旧沙盒可连接：直接复用，不新建。"""
    fake_sandbox.registered.add("sbx-alive")
    set_game_sandbox(session_factory, thread.game_id, "sbx-alive")
    cos = FakeCos()

    result = _ensure(session=session, thread_id=thread.thread_id, cos=cos)

    assert result["sandbox_id"] == "sbx-alive"
    assert result["created"] is False
    assert result["game_id"] == thread.game_id
    assert fake_sandbox.created == []
    assert [sandbox_id for sandbox_id, _ in fake_sandbox.command_log] == ["sbx-alive"]
    assert cos.ensured_prefixes == [str(thread.game_id)]
    assert read_game_sandbox(session_factory, thread.game_id) == "sbx-alive"


def test_recreate_when_sandbox_dead(
    session: Session,
    session_factory: sessionmaker[Session],
    thread: GameThread,
    fake_sandbox: type[FakeSandbox],
) -> None:
    """旧沙盒已回收：新建实例、写回 games.sandbox_id，并带上挂载与环境变量。"""
    set_game_sandbox(session_factory, thread.game_id, "sbx-dead")

    result = _ensure(session=session, thread_id=thread.thread_id)

    assert result["created"] is True
    assert result["sandbox_id"] == "sbx-1"
    assert fake_sandbox.created == ["sbx-1"]

    kwargs = fake_sandbox.created_kwargs[0]
    assert kwargs["template"] == TEMPLATE
    assert kwargs["timeout"] == TIMEOUT_SECONDS
    metadata = kwargs["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["game_id"] == str(thread.game_id)
    assert "x-mounts" in metadata
    envs = kwargs["envs"]
    assert isinstance(envs, dict)
    assert envs["PORT"] == "3000"
    assert str(envs["DATABASE_URL"]).startswith("postgresql://game_")

    assert [sandbox_id for sandbox_id, _ in fake_sandbox.command_log] == ["sbx-1"]
    assert read_game_sandbox(session_factory, thread.game_id) == "sbx-1"


def test_concurrent_ensure_creates_single_sandbox(
    session_factory: sessionmaker[Session],
    thread: GameThread,
    fake_sandbox: type[FakeSandbox],
) -> None:
    """回归：并发 ensure（旧沙盒已回收）只创建一个沙盒，另一个请求复用它。"""
    fake_sandbox.create_delay = 0.4  # 复现真实 create 的耗时窗口（实测 ~4.6s）
    set_game_sandbox(session_factory, thread.game_id, "sbx-dead")

    results: dict[int, dict[str, Any]] = {}
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def worker(index: int) -> None:
        try:
            with session_factory() as session:
                barrier.wait(timeout=10)  # 两个请求同时进入 ensure
                results[index] = _ensure(session=session, thread_id=thread.thread_id)
        except BaseException as exc:  # noqa: BLE001  线程内异常带回主线程断言
            errors.append(exc)

    workers = [threading.Thread(target=worker, args=(index,)) for index in range(2)]
    for worker_thread in workers:
        worker_thread.start()
    for worker_thread in workers:
        worker_thread.join(timeout=30)

    assert errors == []
    assert len(results) == 2
    assert fake_sandbox.created == ["sbx-1"], "并发 ensure 只能创建一个沙盒"
    assert {item["sandbox_id"] for item in results.values()} == {"sbx-1"}
    assert sorted(item["created"] for item in results.values()) == [False, True]
    assert read_game_sandbox(session_factory, thread.game_id) == "sbx-1"


def test_lock_emits_for_update(session: Session, game: Game) -> None:
    """守住 `with_for_update=True`：对象已在 identity map 时也必须真的发出 FOR UPDATE。"""
    statements: list[str] = []

    def capture(
        conn: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        statements.append(" ".join(statement.split()))

    bind = session.get_bind()
    event.listen(bind, "before_cursor_execute", capture)
    try:
        session.get(Game, game.game_id)  # 先放进 identity map
        statements.clear()
        locked = game_repository.lock(session, game_id=game.game_id)
        assert locked is not None
        assert any("FOR UPDATE" in sql.upper() for sql in statements), statements
    finally:
        event.remove(bind, "before_cursor_execute", capture)
        session.rollback()
