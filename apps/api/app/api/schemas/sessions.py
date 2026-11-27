import uuid

from pydantic import BaseModel


class PreviewResponse(BaseModel):
    thread_id: uuid.UUID
    novnc_url: str


class RenewSandboxResponse(BaseModel):
    thread_id: uuid.UUID
    sandbox_id: str | None
    renewed: bool
    timeout_seconds: int
