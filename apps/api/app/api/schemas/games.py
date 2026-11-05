import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateGameBody(BaseModel):
    name: str = ""


class GameResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    game_id: uuid.UUID
    name: str
    status: str
    sandbox_id: str | None
    public_url: str | None
    created_at: datetime
    updated_at: datetime


class CreateThreadBody(BaseModel):
    title: str = ""


class RenameThreadBody(BaseModel):
    """会话重命名：与参考前端新建框保持一致，最长 64 字。"""

    title: str = Field(min_length=1, max_length=64)


class ThreadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    thread_id: uuid.UUID
    game_id: uuid.UUID
    title: str
    status: str
    created_at: datetime
    updated_at: datetime


class VersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_id: uuid.UUID
    seq: int
    status: str
    note: str
    revision: str | None
    created_at: datetime
    deployed_at: datetime | None
