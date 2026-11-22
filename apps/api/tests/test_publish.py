"""发布链路：异步受理、PG 咨询锁互斥、后台执行与状态查询。"""

import threading
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import (
    get_ags,
    get_cos,
    get_pg_admin,
    get_publish_executor,
    get_tcb,
)
from app.core.config import Settings
from app.core.constants import PUBLISH_JOB_TTL_SECONDS
from app.core.exceptions import ConflictError
from app.core.security import create_access_token
from app.gateways.ags import AgsGateway
from app.main import create_app
from app.models.game import Game
from app.models.thread import GameThread
from app.models.user import User
from app.repositories.version_repository import version_repository
from app.services import publish_service
from tests.fakes import FakeCos, FakeExecutor, FakePgAdmin, FakeSandbox, FakeTcb

PUBLISH_PATH = "/api/v1/internal/games/publish"
STATUS_PATH = "/api/v1/internal/games/publish/status"
AGENT_TIMEOUT_SECONDS = 3600


def _seed_workspace(cos: FakeCos, game_id: uuid.UUID) -> None:
    cos.put_bytes(f"games/{game_id}/package.json", b'{"name":"game"}')
    cos.put_bytes(f"games/{game_id}/src/main.js", b'console.log("hi")')


@pytest.fixture
def fake_cos() -> FakeCos:
    return FakeCos()


@pytest.fixture
def fake_tcb() -> FakeTcb:
    return FakeTcb()


@pytest.fixture
def fake_executor() -> FakeExecutor:
    return FakeExecutor()


@pytest.fixture
def ags(fake_sandbox: type[FakeSandbox]) -> AgsGateway:
    return AgsGateway(
        domain="test.ags.local",
        api_key="test-key",
        template="sdt-test",
        timeout_seconds=AGENT_TIMEOUT_SECONDS,
    )


@pytest.fixture
def api_client(
    settings: Settings,
    fake_sandbox: type[FakeSandbox],
    fake_cos: FakeCos,
    fake_tcb: FakeTcb,
    fake_executor: FakeExecutor,
) -> Iterator[TestClient]:
    application = create_app(settings)
    application.dependency_overrides[get_ags] = lambda: AgsGateway(
        domain="test.ags.local",
        api_key="test-key",
        template="sdt-test",
        timeout_seconds=AGENT_TIMEOUT_SECONDS,
    )
    application.dependency_overrides[get_cos] = lambda: fake_cos
    application.dependency_overrides[get_tcb] = lambda: fake_tcb
    application.dependency_overrides[get_pg_admin] = FakePgAdmin
    application.dependency_overrides[get_publish_executor] = lambda: fake_executor
    with TestClient(application) as client:
        yield client


def _start(game_id: uuid.UUID, thread_id: uuid.UUID, session: Session) -> uuid.UUID:
    version = publish_service.start_publish(
        game_id=game_id,
        source_thread_id=thread_id,
        name="测试发布",
        session=session,
    )
    return version.version_id


def test_start_creates_deploying_version(session: Session, game: Game, thread: GameThread) -> None:
    version = publish_service.start_publish(
        game_id=game.game_id,
        source_thread_id=thread.thread_id,
        name="第一版",
        session=session,
    )

    assert version.status == "deploying"
    assert version.seq == 1
    assert version.note == "第一版"
    assert version_repository.latest_for_game(session, game.game_id) is not None


def test_second_publish_conflicts(
    session_factory: sessionmaker[Session], game: Game, thread: GameThread
) -> None:
    with session_factory() as first:
        _start(game.game_id, thread.thread_id, first)

    with session_factory() as second:
        with pytest.raises(ConflictError, match="已有发布正在进行"):
            _start(game.game_id, thread.thread_id, second)

    with session_factory() as check:
        assert len(version_repository.list_by_game(check, game.game_id)) == 1


def test_concurrent_publish_only_one_accepted(
    session_factory: sessionmaker[Session], game: Game, thread: GameThread
) -> None:
    barrier = threading.Barrier(2)

    def attempt() -> str:
        barrier.wait()
        with session_factory() as session:
            try:
                _start(game.game_id, thread.thread_id, session)
            except ConflictError:
                return "conflict"
        return "accepted"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))

    assert sorted(results) == ["accepted", "conflict"]
    with session_factory() as check:
        versions = version_repository.list_by_game(check, game.game_id)
        assert len(versions) == 1
        assert versions[0].status == "deploying"


def test_publish_lock_rejects_concurrent_critical_section(
    session_factory: sessionmaker[Session], game: Game, thread: GameThread
) -> None:
    with session_factory() as locker:
        assert version_repository.acquire_publish_lock(locker, game_id=game.game_id) is True
        with session_factory() as contender:
            with pytest.raises(ConflictError, match="发布请求正在处理中"):
                _start(game.game_id, thread.thread_id, contender)
        locker.rollback()


def test_execute_publish_success(
    session_factory: sessionmaker[Session],
    session: Session,
    game: Game,
    thread: GameThread,
    fake_cos: FakeCos,
    fake_tcb: FakeTcb,
    ags: AgsGateway,
) -> None:
    _seed_workspace(fake_cos, game.game_id)
    version_id = _start(game.game_id, thread.thread_id, session)

    publish_service.execute_publish(
        version_id=version_id,
        session_factory=session_factory,
        cos=fake_cos,
        tcb=fake_tcb,
        ags=ags,
        pg_admin=FakePgAdmin(),
    )

    with session_factory() as check:
        version = version_repository.get(check, version_id)
        saved_game = check.get(Game, game.game_id)
        assert version is not None
        assert version.status == "deployed"
        assert version.revision == "pkg-1"
        assert version.deployed_at is not None
        assert saved_game is not None
        assert saved_game.public_url == "https://fake-game.example"

    assert f"games/{game.game_id}/versions/1.tar" in fake_cos.objects
    assert len(fake_tcb.deployments) == 1
    assert fake_tcb.deployments[0]["env_params"]["PORT"] == "3000"
    assert fake_tcb.probed == ["https://fake-game.example"]


def test_execute_publish_marks_failed(
    session_factory: sessionmaker[Session],
    session: Session,
    game: Game,
    thread: GameThread,
    fake_cos: FakeCos,
    fake_tcb: FakeTcb,
    ags: AgsGateway,
) -> None:
    _seed_workspace(fake_cos, game.game_id)
    fake_tcb.fail = True
    version_id = _start(game.game_id, thread.thread_id, session)

    publish_service.execute_publish(
        version_id=version_id,
        session_factory=session_factory,
        cos=fake_cos,
        tcb=fake_tcb,
        ags=ags,
        pg_admin=FakePgAdmin(),
    )

    with session_factory() as check:
        version = version_repository.get(check, version_id)
        saved_game = check.get(Game, game.game_id)
        assert version is not None
        assert version.status == "failed"
        assert saved_game is not None
        assert saved_game.public_url is None


def test_stale_deploying_is_reaped_then_new_publish_allowed(
    session_factory: sessionmaker[Session], game: Game, thread: GameThread
) -> None:
    with session_factory() as first_session:
        first_id = _start(game.game_id, thread.thread_id, first_session)
    with session_factory() as stale:
        first = version_repository.get(stale, first_id)
        assert first is not None
        first.created_at = datetime.now(UTC) - timedelta(seconds=PUBLISH_JOB_TTL_SECONDS + 1)
        stale.commit()

    with session_factory() as second_session:
        second_id = _start(game.game_id, thread.thread_id, second_session)

    with session_factory() as check:
        first = version_repository.get(check, first_id)
        second = version_repository.get(check, second_id)
        assert first is not None and first.status == "failed"
        assert second is not None and second.status == "deploying"
        assert second.seq == 2


def test_fail_all_deploying_on_startup(
    session_factory: sessionmaker[Session], session: Session, game: Game, thread: GameThread
) -> None:
    version_id = _start(game.game_id, thread.thread_id, session)

    with session_factory() as reconcile:
        assert version_repository.fail_all_deploying(reconcile) == 1

    with session_factory() as check:
        version = version_repository.get(check, version_id)
        assert version is not None and version.status == "failed"


def test_internal_publish_is_async_and_conflicts(
    api_client: TestClient,
    fake_executor: FakeExecutor,
    thread: GameThread,
    internal_headers: dict[str, str],
) -> None:
    payload = {"thread_id": str(thread.thread_id), "name": "接口发布"}

    response = api_client.post(PUBLISH_PATH, json=payload, headers=internal_headers)
    assert response.status_code == 202
    body = response.json()
    assert body["seq"] == 1
    assert body["status"] == "deploying"
    assert body["public_url"] is None
    assert len(fake_executor.submitted) == 1

    conflict = api_client.post(PUBLISH_PATH, json=payload, headers=internal_headers)
    assert conflict.status_code == 409
    assert "已有发布正在进行" in conflict.json()["detail"]


def test_internal_publish_requires_token(api_client: TestClient, thread: GameThread) -> None:
    response = api_client.post(PUBLISH_PATH, json={"thread_id": str(thread.thread_id)})
    assert response.status_code == 403


def test_internal_publish_status(
    api_client: TestClient,
    session: Session,
    game: Game,
    thread: GameThread,
    internal_headers: dict[str, str],
) -> None:
    version = publish_service.start_publish(
        game_id=game.game_id,
        source_thread_id=thread.thread_id,
        name="状态",
        session=session,
    )

    response = api_client.get(
        STATUS_PATH, params={"thread_id": str(thread.thread_id)}, headers=internal_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["deploying"] is True
    assert body["version"]["version_id"] == str(version.version_id)
    assert body["version"]["status"] == "deploying"


def test_public_publish_requires_ownership(
    api_client: TestClient,
    session: Session,
    game: Game,
    thread: GameThread,
    user: User,
) -> None:
    token, _ = create_access_token(str(user.user_id))
    headers = {"Authorization": f"Bearer {token}"}

    response = api_client.post(
        f"/api/v1/games/{game.game_id}/publish",
        json={"thread_id": str(thread.thread_id)},
        headers=headers,
    )
    assert response.status_code == 202
    assert response.json()["seq"] == 1

    stranger = User(username=f"stranger-{uuid.uuid4().hex[:8]}", password_hash="x")
    session.add(stranger)
    session.commit()
    stranger_token, _ = create_access_token(str(stranger.user_id))
    forbidden = api_client.post(
        f"/api/v1/games/{game.game_id}/publish",
        json={"thread_id": str(thread.thread_id)},
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert forbidden.status_code == 403
