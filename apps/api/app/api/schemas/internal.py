"""内部接口（agent → api）请求 / 响应模型：**唯一权威**。

agent 侧本地模型必须与此保持一致。
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class EnsureSessionBody(BaseModel):
    thread_id: uuid.UUID


class EnsureSessionResponse(BaseModel):
    thread_id: uuid.UUID
    game_id: uuid.UUID
    sandbox_id: str
    created: bool


class ProvisionDatabaseBody(BaseModel):
    thread_id: uuid.UUID


class ProvisionDatabaseResponse(BaseModel):
    game_id: uuid.UUID
    database_url: str


class PublishGameBody(BaseModel):
    thread_id: uuid.UUID
    name: str = ""


class PublishGameResponse(BaseModel):
    """异步受理结果：版本已创建，部署在后台进行。"""

    game_id: uuid.UUID
    version_id: uuid.UUID
    seq: int
    status: str
    public_url: str | None


class PublishVersionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_id: uuid.UUID
    seq: int
    status: str
    note: str
    revision: str | None
    created_at: datetime
    deployed_at: datetime | None


class PublishStatusResponse(BaseModel):
    game_id: uuid.UUID
    public_url: str | None
    deploying: bool
    version: PublishVersionInfo | None


class SaveGameMapBody(BaseModel):
    """整张覆盖保存玩法图；节点/连线内容由服务层逐项校验。"""

    thread_id: uuid.UUID
    title: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class SaveGameMapResponse(BaseModel):
    game_id: uuid.UUID
    map_id: str
    title: str
    revision: int
    node_count: int
    edge_count: int
    updated_at: datetime
