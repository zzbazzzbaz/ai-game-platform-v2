import uuid

from fastapi import APIRouter

from app.api.dependencies import CosDep, PgAdminDep, SessionDep, UserIdDep
from app.api.schemas.games import (
    CreateGameBody,
    CreateThreadBody,
    GameResponse,
    ThreadResponse,
    VersionResponse,
)
from app.services import game_service

router = APIRouter(prefix="/games", tags=["games"])


@router.get("", response_model=list[GameResponse])
def list_games(session: SessionDep, user_id: UserIdDep) -> list:
    return game_service.list_games(owner_id=user_id, session=session)


@router.post("", response_model=GameResponse)
def create_game(
    body: CreateGameBody,
    session: SessionDep,
    user_id: UserIdDep,
    cos: CosDep,
    pg_admin: PgAdminDep,
) -> dict:
    return game_service.create_game(
        owner_id=user_id, name=body.name, session=session, cos=cos, pg_admin=pg_admin
    )


@router.get("/{game_id}", response_model=GameResponse)
def get_game(game_id: uuid.UUID, session: SessionDep, user_id: UserIdDep) -> dict:
    return game_service.get_owned_game(owner_id=user_id, game_id=game_id, session=session)


@router.get("/{game_id}/threads", response_model=list[ThreadResponse])
def list_threads(game_id: uuid.UUID, session: SessionDep, user_id: UserIdDep) -> list:
    return game_service.list_threads(owner_id=user_id, game_id=game_id, session=session)


@router.post("/{game_id}/threads", response_model=ThreadResponse)
def create_thread(
    game_id: uuid.UUID, body: CreateThreadBody, session: SessionDep, user_id: UserIdDep
) -> dict:
    return game_service.create_thread(
        owner_id=user_id, game_id=game_id, title=body.title, session=session
    )


@router.get("/{game_id}/versions", response_model=list[VersionResponse])
def list_versions(game_id: uuid.UUID, session: SessionDep, user_id: UserIdDep) -> list:
    return game_service.list_versions(owner_id=user_id, game_id=game_id, session=session)
