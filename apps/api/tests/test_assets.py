"""资源上传接口：预签名、完成校验、列举、删除。"""

import uuid
from collections.abc import Iterator
from typing import cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_cos
from app.core.config import Settings
from app.core.security import create_access_token
from app.main import create_app
from app.models.game import Game
from app.models.user import User
from tests.fakes import FakeCos

PRESIGN_PATH = "/api/v1/games/{game_id}/assets/presign"
COMPLETE_PATH = "/api/v1/games/{game_id}/assets/{asset_id}/complete"
ASSETS_PATH = "/api/v1/games/{game_id}/assets"


@pytest.fixture
def fake_cos() -> FakeCos:
    return FakeCos()


@pytest.fixture
def api_client(settings: Settings, fake_cos: FakeCos) -> Iterator[TestClient]:
    application = create_app(settings)
    application.dependency_overrides[get_cos] = lambda: fake_cos
    with TestClient(application) as client:
        yield client


@pytest.fixture
def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(str(user.user_id))
    return {"Authorization": f"Bearer {token}"}


def _presign(
    client: TestClient,
    headers: dict[str, str],
    game_id: uuid.UUID,
    *,
    filename: str = "cover.png",
    content_type: str = "image/png",
    size: int = 1024,
) -> dict[str, object]:
    response = client.post(
        PRESIGN_PATH.format(game_id=game_id),
        headers=headers,
        json={"filename": filename, "content_type": content_type, "size": size},
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, object], response.json())


def test_presign_requires_login(api_client: TestClient, game: Game) -> None:
    response = api_client.post(
        PRESIGN_PATH.format(game_id=game.game_id),
        json={"filename": "a.png", "content_type": "image/png", "size": 1},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "缺少登录凭证"


def test_presign_rejects_other_users_game(
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
        PRESIGN_PATH.format(game_id=other_game.game_id),
        headers=auth_headers,
        json={"filename": "a.png", "content_type": "image/png", "size": 1},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "无权访问该游戏"


def test_presign_sanitizes_path_traversal(
    api_client: TestClient,
    auth_headers: dict[str, str],
    game: Game,
    fake_cos: FakeCos,
    settings: Settings,
) -> None:
    data = _presign(
        api_client, auth_headers, game.game_id, filename="../../secret.txt", content_type="text/plain"
    )

    assert data["filename"] == "secret.txt"
    assert "../" not in str(data["key"])
    assert str(data["key"]).endswith("/secret.txt")
    assert data["sandbox_path"] == f"/workspace/input/{data['asset_id']}/secret.txt"
    assert data["method"] == "PUT"
    assert data["headers"] == {"Content-Type": "text/plain"}
    assert fake_cos.presigned[0]["expires_seconds"] == settings.asset_presign_expires_seconds


def test_presign_rejects_oversize(
    api_client: TestClient,
    auth_headers: dict[str, str],
    game: Game,
    settings: Settings,
) -> None:
    response = api_client.post(
        PRESIGN_PATH.format(game_id=game.game_id),
        headers=auth_headers,
        json={
            "filename": "big.bin",
            "content_type": "application/octet-stream",
            "size": settings.asset_max_upload_bytes + 1,
        },
    )
    assert response.status_code == 400
    assert "超过大小限制" in response.json()["detail"]


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("run.sh", "text/plain"),
        ("a.exe", "application/octet-stream"),
        ("a.png", "application/x-msdownload"),
    ],
)
def test_presign_rejects_unsafe_files(
    api_client: TestClient,
    auth_headers: dict[str, str],
    game: Game,
    filename: str,
    content_type: str,
) -> None:
    response = api_client.post(
        PRESIGN_PATH.format(game_id=game.game_id),
        headers=auth_headers,
        json={"filename": filename, "content_type": content_type, "size": 1},
    )
    assert response.status_code == 400


def test_complete_success(
    api_client: TestClient,
    auth_headers: dict[str, str],
    game: Game,
    fake_cos: FakeCos,
) -> None:
    presigned = _presign(api_client, auth_headers, game.game_id)
    key = str(presigned["key"])
    fake_cos.add_object(key, size=1024, content_type="image/png")

    response = api_client.post(
        COMPLETE_PATH.format(game_id=game.game_id, asset_id=presigned["asset_id"]),
        headers=auth_headers,
        json={"filename": presigned["filename"]},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "asset_id": presigned["asset_id"],
        "filename": "cover.png",
        "key": key,
        "size": 1024,
        "content_type": "image/png",
        "sandbox_path": presigned["sandbox_path"],
    }


def test_complete_missing_object(
    api_client: TestClient,
    auth_headers: dict[str, str],
    game: Game,
) -> None:
    presigned = _presign(api_client, auth_headers, game.game_id)

    response = api_client.post(
        COMPLETE_PATH.format(game_id=game.game_id, asset_id=presigned["asset_id"]),
        headers=auth_headers,
        json={"filename": presigned["filename"]},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "上传未完成或文件不存在"


def test_complete_oversize_deletes_object(
    api_client: TestClient,
    auth_headers: dict[str, str],
    game: Game,
    fake_cos: FakeCos,
    settings: Settings,
) -> None:
    presigned = _presign(api_client, auth_headers, game.game_id)
    key = str(presigned["key"])
    fake_cos.add_object(key, size=settings.asset_max_upload_bytes + 1, content_type="image/png")

    response = api_client.post(
        COMPLETE_PATH.format(game_id=game.game_id, asset_id=presigned["asset_id"]),
        headers=auth_headers,
        json={"filename": presigned["filename"]},
    )

    assert response.status_code == 400
    assert key in fake_cos.deleted
    assert key not in fake_cos.objects


def test_list_assets_skips_placeholder(
    api_client: TestClient,
    auth_headers: dict[str, str],
    game: Game,
    fake_cos: FakeCos,
) -> None:
    presigned = _presign(api_client, auth_headers, game.game_id)
    fake_cos.add_object(str(presigned["key"]), size=1024, content_type="image/png")
    fake_cos.add_object(f"games/{game.game_id}/input/.keep", size=0, content_type="application/octet-stream")

    response = api_client.get(ASSETS_PATH.format(game_id=game.game_id), headers=auth_headers)

    assert response.status_code == 200, response.text
    items = response.json()
    assert len(items) == 1
    assert items[0]["asset_id"] == presigned["asset_id"]
    assert items[0]["filename"] == "cover.png"
    assert items[0]["size"] == 1024


def test_delete_asset_removes_directory(
    api_client: TestClient,
    auth_headers: dict[str, str],
    game: Game,
    fake_cos: FakeCos,
) -> None:
    presigned = _presign(api_client, auth_headers, game.game_id)
    prefix = f"games/{game.game_id}/input/{presigned['asset_id']}/"
    fake_cos.add_object(f"{prefix}cover.png", size=1, content_type="image/png")
    fake_cos.add_object(f"{prefix}extra.txt", size=1, content_type="text/plain")

    response = api_client.delete(
        f"/api/v1/games/{game.game_id}/assets/{presigned['asset_id']}", headers=auth_headers
    )

    assert response.status_code == 204
    assert fake_cos.list_keys(prefix) == []
