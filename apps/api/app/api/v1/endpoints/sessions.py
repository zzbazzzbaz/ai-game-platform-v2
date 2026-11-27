import uuid
from typing import Any

from fastapi import APIRouter

from app.api.dependencies import AgsDep, CosDep, PgAdminDep, SessionDep, UserIdDep
from app.api.schemas.sessions import PreviewResponse, RenewSandboxResponse
from app.services import game_service, sandbox_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/{thread_id}/preview", response_model=PreviewResponse)
def preview(
    thread_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
    ags: AgsDep,
    cos: CosDep,
    pg_admin: PgAdminDep,
) -> dict[str, Any]:
    """开发期预览：直接返回沙盒 NoVNC 地址（含令牌；上线前改同源反代）。"""
    game_service.get_owned_thread(owner_id=user_id, thread_id=thread_id, session=session)
    return sandbox_service.preview_url_for_thread(
        thread_id=thread_id, session=session, ags=ags, cos=cos, pg_admin=pg_admin
    )


@router.post("/{thread_id}/sandbox/renew", response_model=RenewSandboxResponse)
def renew_sandbox(
    thread_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
    ags: AgsDep,
) -> dict[str, Any]:
    """前端轮询续期：把沙盒剩余租期设为 5 分钟；没有沙盒时返回 renewed=False。"""
    game_service.get_owned_thread(owner_id=user_id, thread_id=thread_id, session=session)
    return sandbox_service.renew_sandbox_for_thread(
        thread_id=thread_id, session=session, ags=ags
    )
