"""沙盒续期接口：前端轮询，每次把剩余租期设为 5 分钟。"""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_ags
from app.core.config import Settings
from app.core.security import create_access_token
from app.gateways.ags import AgsGateway
from app.main import create_app
from app.models.game import Game
from app.models.thread import GameThread
from app.models.user import User
from tests.fakes import FakeSandbox, set_game_sandbox

RENEW_PATH = "/api/v1/sessions/{thread_id}/sandbox/renew"
TIMEOUT_SECONDS = 3600


@pytest.fixture
def api_client(settings: Settings, fake_sandbox: type[FakeSandbox]) -> Iterator[TestClient]:
    application = create_app(settings)
    application.dependency_overrides[get_ags] = lambda: AgsGateway(
        domain="test.ags.local",
        api_key="test-key",
        template="sdt-test",
        timeout_seconds=TIMEOUT_SECONDS,
    )
    with TestClient(application) as client:
        yield client


@pytest.fixture
def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(str(user.user_id))
    return {"Authorization": f"Bearer {token}"}


def test_renew_without_sandbox_returns_not_renewed(
    api_client: TestClient, auth_headers: dict[str, str], thread: GameThread
) -> None:
    response = api_client.post(RENEW_PATH.format(thread_id=thread.thread_id), headers=auth_headers)

    assert response.status_code == 200, response.text
    assert response.json() == {
        "thread_id": str(thread.thread_id),
        "sandbox_id": None,
        "renewed": False,
        "timeout_seconds": 300,
    }


def test_renew_sets_five_minutes(
    api_client: TestClient,
    auth_headers: dict[str, str],
    session_factory: sessionmaker[Session],
    game: Game,
    thread: GameThread,
    fake_sandbox: type[FakeSandbox],
) -> None:
    set_game_sandbox(session_factory, game.game_id, "sbx-live")
    fake_sandbox.registered.add("sbx-live")

    response = api_client.post(RENEW_PATH.format(thread_id=thread.thread_id), headers=auth_headers)

    assert response.status_code == 200, response.text
    assert response.json()["renewed"] is True
    assert response.json()["timeout_seconds"] == 300
    assert fake_sandbox.timeouts == [("sbx-live", 300)]


def test_renew_expired_sandbox_returns_not_renewed(
    api_client: TestClient,
    auth_headers: dict[str, str],
    session_factory: sessionmaker[Session],
    game: Game,
    thread: GameThread,
) -> None:
    set_game_sandbox(session_factory, game.game_id, "sbx-dead")

    response = api_client.post(RENEW_PATH.format(thread_id=thread.thread_id), headers=auth_headers)

    assert response.status_code == 200, response.text
    assert response.json()["sandbox_id"] == "sbx-dead"
    assert response.json()["renewed"] is False


def test_renew_requires_owner(
    api_client: TestClient, session: Session, thread: GameThread
) -> None:
    other = User(username=f"other-{uuid.uuid4().hex[:8]}", password_hash="x")
    session.add(other)
    session.commit()
    token, _ = create_access_token(str(other.user_id))

    response = api_client.post(
        RENEW_PATH.format(thread_id=thread.thread_id),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "无权访问该会话"
