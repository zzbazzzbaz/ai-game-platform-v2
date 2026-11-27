"""公开玩法图接口模型（前端直接读取）。"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import GAME_MAP_DEFAULT_EDGE_KIND, GAME_MAP_DEFAULT_NODE_KIND


class MapNodePayload(BaseModel):
    id: str
    title: str
    detail: str = ""
    attributes: list[str] = Field(default_factory=list)
    kind: str = GAME_MAP_DEFAULT_NODE_KIND


class MapEdgePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    to: str
    title: str = ""
    detail: str = ""
    attributes: list[str] = Field(default_factory=list)
    kind: str = GAME_MAP_DEFAULT_EDGE_KIND


class GameMapDetailResponse(BaseModel):
    game_id: uuid.UUID
    map_id: str
    title: str
    revision: int
    nodes: list[MapNodePayload]
    edges: list[MapEdgePayload]
    created_at: datetime
    updated_at: datetime
