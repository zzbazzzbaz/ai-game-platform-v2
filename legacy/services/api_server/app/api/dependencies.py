from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.security import verify_token
from app.gateways.minio import MinioGateway
from app.gateways.modal import ModalGateway


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise


def get_modal(request: Request) -> ModalGateway:
    return request.app.state.modal


def get_minio(request: Request) -> MinioGateway:
    return request.app.state.minio


def _bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def require_user(request: Request) -> str:
    user_id = verify_token(_bearer(request) or "")
    if user_id is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return user_id


SessionDep = Annotated[Session, Depends(get_session)]
ModalDep = Annotated[ModalGateway, Depends(get_modal)]
MinioDep = Annotated[MinioGateway, Depends(get_minio)]
UserIdDep = Annotated[str, Depends(require_user)]
