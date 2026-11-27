"""内部玩法图接口：Agent 专用，通过 thread_id 定位游戏。"""

import uuid
from typing import Any

from fastapi import APIRouter

from app.api.dependencies import InternalDep, SessionDep
from app.api.schemas.internal import SaveGameMapBody, SaveGameMapResponse
from app.api.schemas.maps import GameMapDetailResponse
from app.services import map_service

router = APIRouter(prefix="/internal/games/maps", tags=["internal"])


@router.get("", response_model=list[str])
def list_game_maps(
    thread_id: uuid.UUID, session: SessionDep, _: InternalDep
) -> list[str]:
    return map_service.list_map_ids_for_thread(thread_id=thread_id, session=session)


@router.get("/{map_id}", response_model=GameMapDetailResponse)
def get_game_map(
    map_id: str, thread_id: uuid.UUID, session: SessionDep, _: InternalDep
) -> dict[str, Any]:
    return map_service.get_map_detail_for_thread(
        thread_id=thread_id, map_id=map_id, session=session
    )


@router.put("/{map_id}", response_model=SaveGameMapResponse)
def save_game_map(
    map_id: str,
    body: SaveGameMapBody,
    session: SessionDep,
    _: InternalDep,
) -> dict[str, Any]:
    return map_service.save_map_for_thread(
        thread_id=body.thread_id,
        map_id=map_id,
        title=body.title,
        nodes=body.nodes,
        edges=body.edges,
        session=session,
    )
