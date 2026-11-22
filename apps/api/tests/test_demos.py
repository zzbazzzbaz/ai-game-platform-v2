"""体验版派生接口：复制工作区 + 新建游戏/会话/数据库 + 返回提示词。"""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_cos, get_pg_admin
from app.core.config import Settings
from app.core.constants import DEMO_NAME_SUFFIX, DEMO_THREAD_TITLE
from app.core.security import create_access_token
from app.main import create_app
from app.models.game import Game
from app.models.thread import GameThread
from app.models.user import User
from tests.fakes import FakeCos, FakePgAdmin

DEMOS_PATH = "/api/v1/games/{game_id}/demos"


@pytest.fixture
def fake_cos() -> FakeCos:
    return FakeCos()


@pytest.fixture
def fake_pg_admin() -> FakePgAdmin:
    return FakePgAdmin()


@pytest.fixture
def api_client(
    settings: Settings, fake_cos: FakeCos, fake_pg_admin: FakePgAdmin
) -> Iterator[TestClient]:
    application = create_app(settings)
    application.dependency_overrides[get_cos] = lambda: fake_cos
    application.dependency_overrides[get_pg_admin] = lambda: fake_pg_admin
    with TestClient(application) as client:
        yield client


@pytest.fixture
def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(str(user.user_id))
    return {"Authorization": f"Bearer {token}"}


def _seed_workspace(cos: FakeCos, game: Game) -> None:
    prefix = f"games/{game.game_id}/"
    cos.put_bytes(f"{prefix}package.json", b'{"name":"game"}')
    cos.put_bytes(f"{prefix}src/main.js", b'console.log("hi")')
    cos.put_bytes(f"{prefix}shared/logic.js", b"export const x = 1;")
    cos.put_bytes(f"{prefix}versions/1.tar", b"old-version")
    cos.put_bytes(f"{prefix}input/a/cover.png", b"png")
    cos.put_bytes(f"{prefix}dist/game.js", b"built")
    cos.put_bytes(f"{prefix}node_modules/pkg/index.js", b"dep")
    cos.put_bytes(f"{prefix}.runtime/server.log", b"log")


def test_create_demo_copies_workspace_and_creates_game(
    api_client: TestClient,
    auth_headers: dict[str, str],
    session: Session,
    user: User,
    game: Game,
    fake_cos: FakeCos,
    fake_pg_admin: FakePgAdmin,
) -> None:
    game.public_url = "https://full.example"
    session.commit()
    _seed_workspace(fake_cos, game)

    response = api_client.post(DEMOS_PATH.format(game_id=game.game_id), headers=auth_headers)

    assert response.status_code == 201, response.text
    data = response.json()
    demo_id = uuid.UUID(data["game_id"])
    thread_id = uuid.UUID(data["thread_id"])
    assert demo_id != game.game_id
    assert "测试游戏" in data["kickoff_prompt"]
    assert "https://full.example" in data["kickoff_prompt"]
    assert "第 1 关" in data["kickoff_prompt"]

    demo = session.get(Game, demo_id)
    assert demo is not None
    assert demo.owner_id == user.user_id
    assert demo.name == f"测试游戏{DEMO_NAME_SUFFIX}"
    assert demo.sandbox_id is None
    assert demo.public_url is None

    thread = session.get(GameThread, thread_id)
    assert thread is not None
    assert thread.game_id == demo_id
    assert thread.title == DEMO_THREAD_TITLE

    assert fake_pg_admin.ensured == [str(demo_id)]
    new_prefix = f"games/{demo_id}/"
    assert fake_cos.get_bytes(f"{new_prefix}package.json") == b'{"name":"game"}'
    assert fake_cos.get_bytes(f"{new_prefix}src/main.js") == b'console.log("hi")'
    assert fake_cos.get_bytes(f"{new_prefix}shared/logic.js") == b"export const x = 1;"
    assert fake_cos.get_bytes(f"{new_prefix}versions/1.tar") is None
    assert fake_cos.get_bytes(f"{new_prefix}input/a/cover.png") is None
    assert fake_cos.get_bytes(f"{new_prefix}dist/game.js") is None
    assert fake_cos.get_bytes(f"{new_prefix}node_modules/pkg/index.js") is None
    assert fake_cos.get_bytes(f"{new_prefix}.runtime/server.log") is None
    assert fake_cos.get_bytes(f"games/{game.game_id}/src/main.js") == b'console.log("hi")'


def test_create_demo_uses_placeholder_when_parent_not_published(
    api_client: TestClient,
    auth_headers: dict[str, str],
    game: Game,
    fake_cos: FakeCos,
) -> None:
    _seed_workspace(fake_cos, game)

    response = api_client.post(DEMOS_PATH.format(game_id=game.game_id), headers=auth_headers)

    assert response.status_code == 201, response.text
    prompt = response.json()["kickoff_prompt"]
    assert "完整版尚未发布" in prompt
    assert "不要编造链接" in prompt


def test_create_demo_requires_game_code(
    api_client: TestClient,
    auth_headers: dict[str, str],
    session: Session,
    game: Game,
    fake_pg_admin: FakePgAdmin,
) -> None:
    response = api_client.post(DEMOS_PATH.format(game_id=game.game_id), headers=auth_headers)

    assert response.status_code == 400
    assert "还没有游戏代码" in response.json()["detail"]
    assert session.scalars(select(Game).where(Game.owner_id == game.owner_id)).all() == [game]
    assert fake_pg_admin.ensured == []


def test_create_demo_rejects_other_users_game(
    api_client: TestClient,
    auth_headers: dict[str, str],
    session: Session,
) -> None:
    other = User(username=f"other-{uuid.uuid4().hex[:8]}", password_hash="x")
    session.add(other)
    session.commit()
    other_game = Game(owner_id=other.user_id, name="别人的游戏")
    session.add(other_game)
    session.commit()

    response = api_client.post(
        DEMOS_PATH.format(game_id=other_game.game_id), headers=auth_headers
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "无权访问该游戏"


def test_create_demo_requires_login(api_client: TestClient, game: Game) -> None:
    response = api_client.post(DEMOS_PATH.format(game_id=game.game_id))

    assert response.status_code == 401
    assert response.json()["detail"] == "缺少登录凭证"
