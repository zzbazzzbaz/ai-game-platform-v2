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


class PublishGameBody(BaseModel):
    thread_id: uuid.UUID | None = None
    name: str = ""


class CreateDemoResponse(BaseModel):
    """体验版克隆结果：新项目已建好，提示词交给前端在新会话中发送。"""

    game_id: uuid.UUID
    thread_id: uuid.UUID
    kickoff_prompt: str


class PublishResponse(BaseModel):
    """异步受理结果：版本已创建，部署在后台进行。"""

    game_id: uuid.UUID
    version_id: uuid.UUID
    seq: int
    status: str
    public_url: str | None


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
