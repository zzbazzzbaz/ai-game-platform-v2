"""公开玩法图接口：只读；前端直接调用，不经过 Agent。"""

import uuid
from typing import Any

from fastapi import APIRouter

from app.api.dependencies import SessionDep, UserIdDep
from app.api.schemas.maps import GameMapDetailResponse
from app.services import map_service

router = APIRouter(prefix="/games", tags=["maps"])


@router.get("/{game_id}/maps", response_model=list[str])
def list_game_maps(game_id: uuid.UUID, session: SessionDep, user_id: UserIdDep) -> list[str]:
    """列出玩法图 id，不返回标题、节点或时间。"""
    return map_service.list_map_ids(owner_id=user_id, game_id=game_id, session=session)


@router.get("/{game_id}/maps/{map_id}", response_model=GameMapDetailResponse)
def get_game_map(
    game_id: uuid.UUID, map_id: str, session: SessionDep, user_id: UserIdDep
) -> dict[str, Any]:
    """读取一张玩法图的完整内容；不存在或 id 非法都按不存在处理。"""
    return map_service.get_map_detail(
        owner_id=user_id, game_id=game_id, map_id=map_id, session=session
    )
