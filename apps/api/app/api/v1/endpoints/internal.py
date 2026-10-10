import uuid

from fastapi import APIRouter

from app.api.dependencies import (
    AgsDep,
    CosDep,
    InternalDep,
    PgAdminDep,
    SessionDep,
    TcbDep,
)
from app.api.schemas.internal import (
    EnsureSessionBody,
    EnsureSessionResponse,
    ProvisionDatabaseBody,
    ProvisionDatabaseResponse,
    PublishGameBody,
    PublishGameResponse,
    RestartServerResponse,
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
) -> dict:
    return sandbox_service.ensure_for_thread(
        thread_id=body.thread_id, session=session, ags=ags, cos=cos, pg_admin=pg_admin
    )


@router.post("/db/provision", response_model=ProvisionDatabaseResponse)
def provision_database(
    body: ProvisionDatabaseBody, session: SessionDep, pg_admin: PgAdminDep, _: InternalDep
) -> dict:
    return provision_service.provision_database_for_thread(
        thread_id=body.thread_id, session=session, pg_admin=pg_admin
    )


@router.post("/sessions/{thread_id}/server/restart", response_model=RestartServerResponse)
def restart_server(
    thread_id: uuid.UUID, session: SessionDep, ags: AgsDep, _: InternalDep
) -> dict:
    return sandbox_service.restart_server(thread_id=thread_id, session=session, ags=ags)


@router.post("/games/publish", response_model=PublishGameResponse)
def publish_game(
    body: PublishGameBody,
    session: SessionDep,
    tcb: TcbDep,
    cos: CosDep,
    ags: AgsDep,
    pg_admin: PgAdminDep,
    _: InternalDep,
) -> dict:
    return publish_service.publish_game(
        thread_id=body.thread_id,
        name=body.name,
        session=session,
        tcb=tcb,
        cos=cos,
        ags=ags,
        pg_admin=pg_admin,
    )
