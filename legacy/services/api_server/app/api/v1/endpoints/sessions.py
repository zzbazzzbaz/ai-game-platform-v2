from fastapi import APIRouter, UploadFile

from app.api.dependencies import MinioDep, ModalDep, SessionDep, UserIdDep
from app.api.schemas.sessions import (
    EnsureBody,
    EnsureResponse,
    InputResponse,
)
from app.core.constants import BINARY_MEDIA_TYPE, FILE_CHUNK_SIZE, MAX_INPUT_BYTES
from app.core.exceptions import ValidationError
from app.services import publish_service, session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/ensure", response_model=EnsureResponse)
def ensure(
    body: EnsureBody, session: SessionDep, modal: ModalDep, minio: MinioDep, user_id: UserIdDep
) -> dict:
    return session_service.ensure_session(
        thread_id=body.thread_id.strip(),
        user_id=user_id,
        session=session,
        modal=modal,
        minio=minio,
    )


@router.post("/{thread_id}/input", response_model=InputResponse)
def upload_input(
    thread_id: str,
    file: UploadFile,
    session: SessionDep,
    minio: MinioDep,
    user_id: UserIdDep,
) -> dict:
    filename = (file.filename or "").split("/")[-1].split("\\")[-1]
    data = _read_capped(file)
    return publish_service.store_input(
        thread_id=thread_id,
        user_id=user_id,
        filename=filename,
        data=data,
        content_type=file.content_type or BINARY_MEDIA_TYPE,
        session=session,
        minio=minio,
    )


def _read_capped(file: UploadFile) -> bytes:
    if file.size is not None and file.size > MAX_INPUT_BYTES:
        raise ValidationError("素材超过 5MB")
    chunks, total = [], 0
    while True:
        chunk = file.file.read(FILE_CHUNK_SIZE)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > MAX_INPUT_BYTES:
            raise ValidationError("素材超过 5MB")
        chunks.append(chunk)
