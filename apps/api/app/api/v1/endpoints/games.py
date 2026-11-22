import uuid
from typing import Any

from fastapi import APIRouter

from app.api.dependencies import (
    AgsDep,
    CosDep,
    PgAdminDep,
    PublishExecutorDep,
    SessionDep,
    SessionFactoryDep,
    TcbDep,
    UserIdDep,
)
from app.api.schemas.games import (
    CreateGameBody,
    CreateThreadBody,
    GameResponse,
    PublishGameBody,
    PublishResponse,
    RenameThreadBody,
    ThreadResponse,
    VersionResponse,
)
from app.models.game import Game
from app.models.thread import GameThread
from app.models.version import GameVersion
from app.services import game_service, publish_service

router = APIRouter(prefix="/games", tags=["games"])


@router.get("", response_model=list[GameResponse])
def list_games(session: SessionDep, user_id: UserIdDep) -> list[Game]:
    return game_service.list_games(owner_id=user_id, session=session)


@router.post("", response_model=GameResponse)
def create_game(
    body: CreateGameBody,
    session: SessionDep,
    user_id: UserIdDep,
    cos: CosDep,
    pg_admin: PgAdminDep,
) -> Game:
    return game_service.create_game(
        owner_id=user_id, name=body.name, session=session, cos=cos, pg_admin=pg_admin
    )


@router.get("/{game_id}", response_model=GameResponse)
def get_game(game_id: uuid.UUID, session: SessionDep, user_id: UserIdDep) -> Game:
    return game_service.get_owned_game(owner_id=user_id, game_id=game_id, session=session)


@router.get("/{game_id}/threads", response_model=list[ThreadResponse])
def list_threads(game_id: uuid.UUID, session: SessionDep, user_id: UserIdDep) -> list[GameThread]:
    return game_service.list_threads(owner_id=user_id, game_id=game_id, session=session)


@router.post("/{game_id}/threads", response_model=ThreadResponse)
def create_thread(
    game_id: uuid.UUID, body: CreateThreadBody, session: SessionDep, user_id: UserIdDep
) -> GameThread:
    return game_service.create_thread(
        owner_id=user_id, game_id=game_id, title=body.title, session=session
    )


@router.patch("/{game_id}/threads/{thread_id}", response_model=ThreadResponse)
def rename_thread(
    game_id: uuid.UUID,
    thread_id: uuid.UUID,
    body: RenameThreadBody,
    session: SessionDep,
    user_id: UserIdDep,
) -> GameThread:
    return game_service.rename_thread(
        owner_id=user_id,
        game_id=game_id,
        thread_id=thread_id,
        title=body.title,
        session=session,
    )


@router.get("/{game_id}/versions", response_model=list[VersionResponse])
def list_versions(game_id: uuid.UUID, session: SessionDep, user_id: UserIdDep) -> list[GameVersion]:
    return game_service.list_versions(owner_id=user_id, game_id=game_id, session=session)


@router.post("/{game_id}/publish", response_model=PublishResponse, status_code=202)
def publish_game(
    game_id: uuid.UUID,
    body: PublishGameBody,
    session: SessionDep,
    session_factory: SessionFactoryDep,
    executor: PublishExecutorDep,
    user_id: UserIdDep,
    tcb: TcbDep,
    cos: CosDep,
    ags: AgsDep,
    pg_admin: PgAdminDep,
) -> dict[str, Any]:
    game = game_service.get_owned_game(owner_id=user_id, game_id=game_id, session=session)
    thread = publish_service.resolve_source_thread(
        game_id=game.game_id, thread_id=body.thread_id, session=session
    )
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
