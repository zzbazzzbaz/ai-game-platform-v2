import uuid
from typing import Any

from fastapi import APIRouter

from app.api.dependencies import (
    AgsDep,
    CosDep,
    InternalDep,
    PgAdminDep,
    PublishExecutorDep,
    SessionDep,
    SessionFactoryDep,
    TcbDep,
)
from app.api.schemas.internal import (
    EnsureSessionBody,
    EnsureSessionResponse,
    ProvisionDatabaseBody,
    ProvisionDatabaseResponse,
    PublishGameBody,
    PublishGameResponse,
    PublishStatusResponse,
)
from app.services import provision_service, publish_service, sandbox_service

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/sessions/ensure", response_model=EnsureSessionResponse)
def ensure_session(
    body: EnsureSessionBody,
    session: SessionDep,
    ags: AgsDep,
    cos: CosDep,
    pg_admin: PgAdminDep,
    _: InternalDep,
) -> dict[str, Any]:
    return sandbox_service.ensure_for_thread(
        thread_id=body.thread_id, session=session, ags=ags, cos=cos, pg_admin=pg_admin
    )


@router.post("/db/provision", response_model=ProvisionDatabaseResponse)
def provision_database(
    body: ProvisionDatabaseBody, session: SessionDep, pg_admin: PgAdminDep, _: InternalDep
) -> dict[str, Any]:
    return provision_service.provision_database_for_thread(
        thread_id=body.thread_id, session=session, pg_admin=pg_admin
    )


@router.post("/games/publish", response_model=PublishGameResponse, status_code=202)
def publish_game(
    body: PublishGameBody,
    session: SessionDep,
    session_factory: SessionFactoryDep,
    executor: PublishExecutorDep,
    tcb: TcbDep,
    cos: CosDep,
    ags: AgsDep,
    pg_admin: PgAdminDep,
    _: InternalDep,
) -> dict[str, Any]:
    thread, game = publish_service.resolve_thread(thread_id=body.thread_id, session=session)
    version = publish_service.start_publish(
        game_id=game.game_id,
        source_thread_id=thread.thread_id,
        name=body.name,
        session=session,
    )
    publish_service.submit_publish(
        executor=executor,
        version_id=version.version_id,
        session_factory=session_factory,
        cos=cos,
        tcb=tcb,
        ags=ags,
        pg_admin=pg_admin,
    )
    return publish_service.publish_result(game=game, version=version)


@router.get("/games/publish/status", response_model=PublishStatusResponse)
def publish_status(
    thread_id: uuid.UUID,
    session: SessionDep,
    _: InternalDep,
) -> dict[str, Any]:
    return publish_service.get_publish_status(thread_id=thread_id, session=session)
