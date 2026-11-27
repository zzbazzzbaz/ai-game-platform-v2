"""玩法图业务：属于游戏、整张覆盖保存；不计算源码指纹、不判断过期。"""

import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import (
    GAME_MAP_ATTRIBUTE_MAX_LENGTH,
    GAME_MAP_DEFAULT_EDGE_KIND,
    GAME_MAP_DEFAULT_NODE_KIND,
    GAME_MAP_DETAIL_MAX_LENGTH,
    GAME_MAP_EDGE_KINDS,
    GAME_MAP_EDGE_TITLE_MAX_LENGTH,
    GAME_MAP_ID_PATTERN,
    GAME_MAP_MAX_ATTRIBUTES,
    GAME_MAP_MAX_EDGES,
    GAME_MAP_MAX_NODES,
    GAME_MAP_NODE_ID_MAX_LENGTH,
    GAME_MAP_NODE_ID_PATTERN,
    GAME_MAP_NODE_KINDS,
    GAME_MAP_NODE_TITLE_MAX_LENGTH,
    GAME_MAP_TITLE_MAX_LENGTH,
)
from app.core.exceptions import NotFoundError, UnprocessableError
from app.models.game import Game
from app.models.map import GameMap
from app.repositories.game_repository import game_repository
from app.repositories.map_repository import map_repository
from app.repositories.thread_repository import thread_repository
from app.services import game_service


def list_map_ids(*, owner_id: uuid.UUID, game_id: uuid.UUID, session: Session) -> list[str]:
    game_service.get_owned_game(owner_id=owner_id, game_id=game_id, session=session)
    return map_repository.list_ids(session, game_id)


def get_map_detail(
    *, owner_id: uuid.UUID, game_id: uuid.UUID, map_id: str, session: Session
) -> dict[str, Any]:
    game_service.get_owned_game(owner_id=owner_id, game_id=game_id, session=session)
    game_map = map_repository.get(session, game_id=game_id, map_id=map_id)
    if game_map is None:
        raise NotFoundError("玩法图不存在")
    return _detail_payload(game_map)


def list_map_ids_for_thread(*, thread_id: uuid.UUID, session: Session) -> list[str]:
    game = _game_for_thread(thread_id=thread_id, session=session)
    return map_repository.list_ids(session, game.game_id)


def get_map_detail_for_thread(
    *, thread_id: uuid.UUID, map_id: str, session: Session
) -> dict[str, Any]:
    game = _game_for_thread(thread_id=thread_id, session=session)
    game_map = map_repository.get(session, game_id=game.game_id, map_id=map_id)
    if game_map is None:
        raise NotFoundError("玩法图不存在")
    return _detail_payload(game_map)


def save_map_for_thread(
    *,
    thread_id: uuid.UUID,
    map_id: str,
    title: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    session: Session,
) -> dict[str, Any]:
    game = _game_for_thread(thread_id=thread_id, session=session)
    content = _build_content(map_id=map_id, title=title, nodes=nodes, edges=edges)
    game_map = map_repository.upsert(
        session, game_id=game.game_id, map_id=map_id, content=content
    )
    return {
        "game_id": game_map.game_id,
        "map_id": game_map.map_id,
        "title": title,
        "revision": game_map.revision,
        "node_count": len(content["nodes"]),
        "edge_count": len(content["edges"]),
        "updated_at": game_map.updated_at,
    }


def _game_for_thread(*, thread_id: uuid.UUID, session: Session) -> Game:
    thread = thread_repository.get(session, thread_id)
    if thread is None:
        raise NotFoundError("会话不存在")
    game = game_repository.get(session, thread.game_id)
    if game is None:
        raise NotFoundError("会话不存在")
    return game


def _detail_payload(game_map: GameMap) -> dict[str, Any]:
    content = game_map.content or {}
    raw_nodes = content.get("nodes")
    raw_edges = content.get("edges")
    nodes = [_read_node(item) for item in raw_nodes if isinstance(item, dict)] if isinstance(
        raw_nodes, list
    ) else []
    edges = [_read_edge(item) for item in raw_edges if isinstance(item, dict)] if isinstance(
        raw_edges, list
    ) else []
    return {
        "game_id": game_map.game_id,
        "map_id": game_map.map_id,
        "title": content.get("title") or "",
        "revision": game_map.revision,
        "nodes": nodes,
        "edges": edges,
        "created_at": game_map.created_at,
        "updated_at": game_map.updated_at,
    }


def _read_node(raw: dict[str, Any]) -> dict[str, Any]:
    attributes = raw.get("attributes")
    return {
        "id": raw.get("id") or "",
        "title": raw.get("title") or "",
        "detail": raw.get("detail") or "",
        "attributes": attributes if isinstance(attributes, list) else [],
        "kind": raw.get("kind") or GAME_MAP_DEFAULT_NODE_KIND,
    }


def _read_edge(raw: dict[str, Any]) -> dict[str, Any]:
    attributes = raw.get("attributes")
    return {
        "from": raw.get("from") or "",
        "to": raw.get("to") or "",
        "title": raw.get("title") or "",
        "detail": raw.get("detail") or "",
        "attributes": attributes if isinstance(attributes, list) else [],
        "kind": raw.get("kind") or GAME_MAP_DEFAULT_EDGE_KIND,
    }


def _build_content(
    *, map_id: str, title: str, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> dict[str, Any]:
    _check_map_id(map_id)
    _check_title(title)
    if not 1 <= len(nodes) <= GAME_MAP_MAX_NODES:
        raise UnprocessableError(
            f"玩法图至少需要 1 个节点，最多 {GAME_MAP_MAX_NODES} 个节点"
        )
    if len(edges) > GAME_MAP_MAX_EDGES:
        raise UnprocessableError(f"玩法图最多 {GAME_MAP_MAX_EDGES} 条连线")

    cleaned_nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    for index, raw_node in enumerate(nodes, start=1):
        node = _clean_node(raw_node, index=index)
        if node["id"] in node_ids:
            raise UnprocessableError(f"节点 id 重复：{node['id']}")
        node_ids.add(node["id"])
        cleaned_nodes.append(node)

    cleaned_edges = [
        _clean_edge(raw_edge, index=index, node_ids=node_ids)
        for index, raw_edge in enumerate(edges, start=1)
    ]
    return {"id": map_id, "title": title, "nodes": cleaned_nodes, "edges": cleaned_edges}


def _check_map_id(map_id: str) -> None:
    if not isinstance(map_id, str) or re.fullmatch(GAME_MAP_ID_PATTERN, map_id) is None:
        raise UnprocessableError(
            "玩法图 id 必须为 1–32 位小写字母、数字或中划线，"
            "以字母开头、以字母或数字结尾"
        )


def _check_title(title: str) -> None:
    if not isinstance(title, str) or not 1 <= len(title) <= GAME_MAP_TITLE_MAX_LENGTH:
        raise UnprocessableError(
            f"玩法图标题必须为 1–{GAME_MAP_TITLE_MAX_LENGTH} 个字符"
        )


def _clean_node(raw: object, *, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise UnprocessableError(f"第 {index} 个节点格式不正确")
    node_id = raw.get("id")
    if not isinstance(node_id, str) or not node_id:
        raise UnprocessableError(f"第 {index} 个节点缺少 id")
    if (
        len(node_id) > GAME_MAP_NODE_ID_MAX_LENGTH
        or re.fullmatch(GAME_MAP_NODE_ID_PATTERN, node_id) is None
    ):
        raise UnprocessableError(
            f"节点 id 只能包含字母、数字、中划线、下划线，"
            f"且不超过 {GAME_MAP_NODE_ID_MAX_LENGTH} 个字符：{node_id}"
        )
    title = raw.get("title")
    if not isinstance(title, str) or not 1 <= len(title) <= GAME_MAP_NODE_TITLE_MAX_LENGTH:
        raise UnprocessableError(
            f"节点 {node_id} 的标题必须为 1–{GAME_MAP_NODE_TITLE_MAX_LENGTH} 个字符"
        )
    kind = raw.get("kind")
    if kind is None:
        kind = GAME_MAP_DEFAULT_NODE_KIND
    if not isinstance(kind, str) or kind not in GAME_MAP_NODE_KINDS:
        raise UnprocessableError(f"节点 {node_id} 的 kind 不合法：{kind}")
    return {
        "id": node_id,
        "title": title,
        "detail": _clean_text(
            raw,
            "detail",
            label=f"节点 {node_id} 的说明",
            default="",
            max_length=GAME_MAP_DETAIL_MAX_LENGTH,
        ),
        "attributes": _clean_attributes(raw, label=f"节点 {node_id}"),
        "kind": kind,
    }


def _clean_edge(raw: object, *, index: int, node_ids: set[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise UnprocessableError(f"第 {index} 条连线格式不正确")
    source = raw.get("from")
    target = raw.get("to")
    if not isinstance(source, str) or not isinstance(target, str):
        raise UnprocessableError(f"第 {index} 条连线缺少起点或终点")
    if source not in node_ids or target not in node_ids:
        raise UnprocessableError(f"连线 {source} → {target} 引用了不存在的节点")
    kind = raw.get("kind")
    if kind is None:
        kind = GAME_MAP_DEFAULT_EDGE_KIND
    if not isinstance(kind, str) or kind not in GAME_MAP_EDGE_KINDS:
        raise UnprocessableError(f"连线 {source} → {target} 的 kind 不合法：{kind}")
    return {
        "from": source,
        "to": target,
        "title": _clean_text(
            raw,
            "title",
            label=f"连线 {source} → {target} 的标题",
            default="",
            max_length=GAME_MAP_EDGE_TITLE_MAX_LENGTH,
        ),
        "detail": _clean_text(
            raw,
            "detail",
            label=f"连线 {source} → {target} 的说明",
            default="",
            max_length=GAME_MAP_DETAIL_MAX_LENGTH,
        ),
        "attributes": _clean_attributes(raw, label=f"连线 {source} → {target}"),
        "kind": kind,
    }


def _clean_text(
    raw: dict[str, Any], key: str, *, label: str, default: str, max_length: int
) -> str:
    value = raw.get(key)
    if value is None:
        return default
    if not isinstance(value, str):
        raise UnprocessableError(f"{label}必须是文本")
    if len(value) > max_length:
        raise UnprocessableError(f"{label}不能超过 {max_length} 个字符")
    return value


def _clean_attributes(raw: dict[str, Any], *, label: str) -> list[str]:
    value = raw.get("attributes")
    if value is None:
        return []
    if not isinstance(value, list):
        raise UnprocessableError(f"{label}的 attributes 必须是字符串数组")
    if len(value) > GAME_MAP_MAX_ATTRIBUTES:
        raise UnprocessableError(f"{label}的 attributes 最多 {GAME_MAP_MAX_ATTRIBUTES} 项")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise UnprocessableError(f"{label}的 attributes 必须是字符串数组")
        if len(item) > GAME_MAP_ATTRIBUTE_MAX_LENGTH:
            raise UnprocessableError(
                f"{label}的 attributes 每项不能超过 {GAME_MAP_ATTRIBUTE_MAX_LENGTH} 个字符"
            )
        result.append(item)
    return result
