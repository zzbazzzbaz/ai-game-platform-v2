import hmac

from fastapi import APIRouter, Header, HTTPException, Request

from app.api.dependencies import MinioDep, ModalDep, SessionDep, UserIdDep
from app.api.schemas.auth import VerifyResponse
from app.api.schemas.games import PublishSingleGameBody, PublishSingleGameResponse
from app.api.schemas.sessions import SnapshotResponse
from app.core.config import Settings
from app.services import game_service, session_service

router = APIRouter(prefix="/internal", tags=["internal"])


def _check_internal_token(request: Request, token: str) -> None:
    settings: Settings = request.app.state.settings
    if not hmac.compare_digest(token, settings.auth_internal_token):
        raise HTTPException(status_code=403, detail="内部鉴权失败")


@router.get("/verify", response_model=VerifyResponse)
def internal_verify(
    request: Request,
    user_id: UserIdDep,
    x_internal_token: str = Header(default=""),
) -> VerifyResponse:
    _check_internal_token(request, x_internal_token)
    return VerifyResponse(user_id=user_id)


@router.post("/games/single/publish", response_model=PublishSingleGameResponse)
def internal_publish_single_game(
    body: PublishSingleGameBody,
    request: Request,
    session: SessionDep,
    modal: ModalDep,
    minio: MinioDep,
    x_internal_token: str = Header(default=""),
) -> dict:
    _check_internal_token(request, x_internal_token)
    settings: Settings = request.app.state.settings
    return game_service.publish_single_game(
        thread_id=body.thread_id.strip(),
        user_id=body.user_id,
        name=body.name,
        session=session,
        modal=modal,
        minio=minio,
        public_base_url=settings.public_game_base_url,
    )


@router.post("/sessions/{thread_id}/snapshot", response_model=SnapshotResponse)
def internal_session_snapshot(
    thread_id: str,
    request: Request,
    modal: ModalDep,
    minio: MinioDep,
    x_internal_token: str = Header(default=""),
) -> dict:
    """run 结束后由 agent_server 触发的自动快照（增量 + 删除对账）。"""
    _check_internal_token(request, x_internal_token)
    return session_service.auto_snapshot(thread_id=thread_id, modal=modal, minio=minio)
