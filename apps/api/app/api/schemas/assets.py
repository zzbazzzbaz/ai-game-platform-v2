"""资源上传（预签名直传 COS）请求 / 响应模型。"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PresignAssetBody(BaseModel):
    filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    size: int = Field(gt=0)


class PresignAssetResponse(BaseModel):
    asset_id: uuid.UUID
    filename: str
    key: str
    upload_url: str
    method: str = "PUT"
    headers: dict[str, str]
    expires_at: datetime
    sandbox_path: str


class CompleteAssetBody(BaseModel):
    filename: str = Field(min_length=1)


class AssetResponse(BaseModel):
    asset_id: uuid.UUID
    filename: str
    key: str
    size: int
    content_type: str
    sandbox_path: str


class AssetListItem(BaseModel):
    asset_id: uuid.UUID
    filename: str
    key: str
    size: int
    last_modified: datetime | None
    sandbox_path: str
