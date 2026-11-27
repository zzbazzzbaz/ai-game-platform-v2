"""玩法图：内部保存 + 公开 list/get，以及校验与归属。"""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import create_access_token
from app.main import create_app
from app.models.game import Game
from app.models.map import GameMap
from app.models.thread import GameThread
from app.models.user import User

PUBLIC_MAPS_PATH = "/api/v1/games/{game_id}/maps"
PUBLIC_MAP_PATH = "/api/v1/games/{game_id}/maps/{map_id}"
INTERNAL_MAPS_PATH = "/api/v1/internal/games/maps"
INTERNAL_MAP_PATH = "/api/v1/internal/games/maps/{map_id}"

NODES: list[dict[str, Any]] = [
    {
        "id": "start",
        "title": "开一局",
        "detail": "进入游戏，倒计时开始",
        "attributes": ["限时 60 秒"],
        "kind": "start",
    },
    {"id": "settle", "title": "结算"},
]
EDGES: list[dict[str, Any]] = [
    {"from": "start", "to": "settle", "title": "时间到", "kind": "success"}
]


@pytest.fixture
def api_client(settings: Settings) -> Iterator[TestClient]:
    application = create_app(settings)
    with TestClient(application) as client:
        yield client


@pytest.fixture
def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(str(user.user_id))
    return {"Authorization": f"Bearer {token}"}


def _body(
    thread: GameThread,
    *,
    title: str = "怎么玩",
    nodes: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "thread_id": str(thread.thread_id),
        "title": title,
        "nodes": NODES if nodes is None else nodes,
        "edges": EDGES if edges is None else edges,
    }


def _save(
    client: TestClient,
    internal_headers: dict[str, str],
    thread: GameThread,
    map_id: str = "core-loop",
    *,
    title: str = "怎么玩",
    nodes: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
) -> httpx.Response:
    return client.put(
        INTERNAL_MAP_PATH.format(map_id=map_id),
        json=_body(thread, title=title, nodes=nodes, edges=edges),
        headers=internal_headers,
    )


def test_save_and_read_flow(
    api_client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
    internal_headers: dict[str, str],
    game: Game,
    thread: GameThread,
) -> None:
    list_path = PUBLIC_MAPS_PATH.format(game_id=game.game_id)
    detail_path = PUBLIC_MAP_PATH.format(game_id=game.game_id, map_id="core-loop")

    assert api_client.get(list_path, headers=auth_headers).json() == []

    saved = _save(api_client, internal_headers, thread)
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 1
    assert saved.json()["node_count"] == 2
    assert saved.json()["edge_count"] == 1

    listed = api_client.get(list_path, headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json() == ["core-loop"]
    assert all(isinstance(item, str) for item in listed.json())

    detail = api_client.get(detail_path, headers=auth_headers)
    assert detail.status_code == 200, detail.text
    data = detail.json()
    assert data["map_id"] == "core-loop"
    assert data["title"] == "怎么玩"
    assert data["revision"] == 1
    assert data["nodes"] == [
        {
            "id": "start",
            "title": "开一局",
            "detail": "进入游戏，倒计时开始",
            "attributes": ["限时 60 秒"],
            "kind": "start",
        },
        {
            "id": "settle",
            "title": "结算",
            "detail": "",
            "attributes": [],
            "kind": "action",
        },
    ]
    assert data["edges"] == [
        {
            "from": "start",
            "to": "settle",
            "title": "时间到",
            "detail": "",
            "attributes": [],
            "kind": "success",
        }
    ]

    resaved = _save(api_client, internal_headers, thread, title="玩法说明")
    assert resaved.status_code == 200, resaved.text
    assert resaved.json()["revision"] == 2
    assert resaved.json()["title"] == "玩法说明"

    rows = session.scalars(
        select(GameMap).where(GameMap.game_id == game.game_id)
    ).all()
    assert len(rows) == 1
    assert rows[0].revision == 2
    assert api_client.get(list_path, headers=auth_headers).json() == ["core-loop"]
    assert api_client.get(detail_path, headers=auth_headers).json()["title"] == "玩法说明"


def test_list_order_by_created_at_then_map_id(
    api_client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
    game: Game,
) -> None:
    base = datetime.now(UTC)
    for map_id, created_at in [
        ("zeta", base + timedelta(seconds=2)),
        ("alpha", base + timedelta(seconds=2)),
        ("beta", base + timedelta(seconds=1)),
    ]:
        session.add(
            GameMap(
                game_id=game.game_id,
                map_id=map_id,
                content={"id": map_id, "title": map_id, "nodes": [], "edges": []},
                revision=1,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    session.commit()

    response = api_client.get(
        PUBLIC_MAPS_PATH.format(game_id=game.game_id), headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == ["beta", "alpha", "zeta"]


def test_internal_list_and_get(
    api_client: TestClient,
    internal_headers: dict[str, str],
    thread: GameThread,
) -> None:
    assert _save(api_client, internal_headers, thread).status_code == 200

    listed = api_client.get(
        INTERNAL_MAPS_PATH,
        params={"thread_id": str(thread.thread_id)},
        headers=internal_headers,
    )
    assert listed.status_code == 200
    assert listed.json() == ["core-loop"]

    detail = api_client.get(
        INTERNAL_MAP_PATH.format(map_id="core-loop"),
        params={"thread_id": str(thread.thread_id)},
        headers=internal_headers,
    )
    assert detail.status_code == 200
    assert detail.json()["title"] == "怎么玩"
    assert detail.json()["nodes"][0]["id"] == "start"

    missing = api_client.get(
        INTERNAL_MAP_PATH.format(map_id="missing"),
        params={"thread_id": str(thread.thread_id)},
        headers=internal_headers,
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "玩法图不存在"


def test_public_get_missing_or_invalid_map_id_returns_404(
    api_client: TestClient, auth_headers: dict[str, str], game: Game
) -> None:
    for map_id in ("not-created", "Bad_ID"):
        response = api_client.get(
            PUBLIC_MAP_PATH.format(game_id=game.game_id, map_id=map_id),
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "玩法图不存在"


def test_public_requires_owner(
    api_client: TestClient, session: Session, auth_headers: dict[str, str]
) -> None:
    other = User(username=f"other-{uuid.uuid4().hex[:8]}", password_hash="x")
    session.add(other)
    session.commit()
    foreign_game = Game(owner_id=other.user_id, name="别人的游戏")
    session.add(foreign_game)
    session.commit()

    response = api_client.get(
        PUBLIC_MAPS_PATH.format(game_id=foreign_game.game_id), headers=auth_headers
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "无权访问该游戏"


def test_internal_requires_token(api_client: TestClient, thread: GameThread) -> None:
    response = _save(api_client, {}, thread)
    assert response.status_code == 403
    assert response.json()["detail"] == "内部鉴权失败"


def test_internal_unknown_thread_returns_404(
    api_client: TestClient, internal_headers: dict[str, str]
) -> None:
    response = api_client.get(
        INTERNAL_MAPS_PATH,
        params={"thread_id": "00000000-0000-0000-0000-000000000000"},
        headers=internal_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "会话不存在"


@pytest.mark.parametrize(
    ("map_id", "title", "nodes", "edges", "expected"),
    [
        ("Bad_ID", "怎么玩", None, None, "玩法图 id 必须为"),
        ("core-loop", "", None, None, "玩法图标题必须为"),
        ("core-loop", "怎么玩", [], None, "至少需要 1 个节点"),
        (
            "core-loop",
            "怎么玩",
            [{"id": "a", "title": "甲"}, {"id": "a", "title": "乙"}],
            None,
            "节点 id 重复",
        ),
        (
            "core-loop",
            "怎么玩",
            None,
            [{"from": "start", "to": "ghost"}],
            "引用了不存在的节点",
        ),
    ],
)
def test_internal_save_validation(
    api_client: TestClient,
    internal_headers: dict[str, str],
    thread: GameThread,
    map_id: str,
    title: str,
    nodes: list[dict[str, Any]] | None,
    edges: list[dict[str, Any]] | None,
    expected: str,
) -> None:
    response = _save(
        api_client,
        internal_headers,
        thread,
        map_id=map_id,
        title=title,
        nodes=nodes,
        edges=edges,
    )
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert isinstance(detail, str)
    assert expected in detail


def test_map_table_has_no_freshness_columns() -> None:
    columns = set(GameMap.__table__.columns.keys())
    assert columns == {"game_id", "map_id", "content", "revision", "created_at", "updated_at"}
