"""内部接口层：`POST /api/v1/internal/sessions/ensure` 的鉴权与 HTTP 行为。"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_ags, get_cos, get_pg_admin
from app.core.config import Settings
from app.gateways.ags import AgsGateway
from app.main import create_app
from app.models.thread import GameThread
from tests.fakes import FakeCos, FakePgAdmin, FakeSandbox, read_game_sandbox, set_game_sandbox

ENSURE_PATH = "/api/v1/internal/sessions/ensure"
TIMEOUT_SECONDS = 3600


@pytest.fixture
def api_client(settings: Settings, fake_sandbox: type[FakeSandbox]) -> Iterator[TestClient]:
    """真实 FastAPI 应用 + 假外部依赖（lifespan 会把表建到测试库）。"""
    application = create_app(settings)
    application.dependency_overrides[get_ags] = lambda: AgsGateway(
        domain="test.ags.local",
        api_key="test-key",
        template="sdt-test",
        timeout_seconds=TIMEOUT_SECONDS,
    )
    application.dependency_overrides[get_cos] = FakeCos
    application.dependency_overrides[get_pg_admin] = FakePgAdmin
    with TestClient(application) as client:
        yield client


def test_ensure_requires_internal_token(api_client: TestClient, thread: GameThread) -> None:
    response = api_client.post(ENSURE_PATH, json={"thread_id": str(thread.thread_id)})
    assert response.status_code == 403
    assert response.json()["detail"] == "内部鉴权失败"


def test_ensure_rejects_unknown_thread(
    api_client: TestClient, internal_headers: dict[str, str]
) -> None:
    response = api_client.post(
        ENSURE_PATH,
        json={"thread_id": "00000000-0000-0000-0000-000000000000"},
        headers=internal_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "会话不存在"


def test_ensure_recreates_dead_sandbox_over_http(
    api_client: TestClient,
    internal_headers: dict[str, str],
    session_factory: sessionmaker[Session],
    thread: GameThread,
    fake_sandbox: type[FakeSandbox],
) -> None:
    set_game_sandbox(session_factory, thread.game_id, "sbx-dead")

    response = api_client.post(
        ENSURE_PATH, json={"thread_id": str(thread.thread_id)}, headers=internal_headers
    )

    assert response.status_code == 200
    assert response.json() == {
        "thread_id": str(thread.thread_id),
        "game_id": str(thread.game_id),
        "sandbox_id": "sbx-1",
        "created": True,
    }
    assert fake_sandbox.created == ["sbx-1"]
    assert read_game_sandbox(session_factory, thread.game_id) == "sbx-1"
