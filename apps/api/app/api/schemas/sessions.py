import uuid

from pydantic import BaseModel


class PreviewResponse(BaseModel):
    thread_id: uuid.UUID
    novnc_url: str
