from pydantic import BaseModel


class EnsureBody(BaseModel):
    thread_id: str


class EnsureResponse(BaseModel):
    thread_id: str
    sandbox_id: str
    restored_files: int
    manifest_match: bool


class SnapshotResponse(BaseModel):
    thread_id: str
    checkpoint: str
    files: int
    uploaded: int
    deleted: int


class InputResponse(BaseModel):
    filename: str
    size: int
