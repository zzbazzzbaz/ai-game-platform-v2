from pydantic import BaseModel


class PublishSingleGameBody(BaseModel):
    thread_id: str
    user_id: str
    name: str = ""


class PublishSingleGameResponse(BaseModel):
    thread_id: str
    size: int
    url: str
