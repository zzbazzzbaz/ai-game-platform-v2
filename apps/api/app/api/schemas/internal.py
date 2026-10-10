"""内部接口（agent → api）请求 / 响应模型：**唯一权威**。

agent 侧本地模型必须与此保持一致。
"""

import uuid

from pydantic import BaseModel


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
    game_id: uuid.UUID
    public_url: str
    seq: int
