import uuid
from typing import Any

from fastapi import APIRouter

from app.api.dependencies import CosDep, SessionDep, SettingsDep, UserIdDep
from app.api.schemas.assets import (
    AssetListItem,
    AssetResponse,
    CompleteAssetBody,
    PresignAssetBody,
    PresignAssetResponse,
)
from app.services import asset_service

router = APIRouter(prefix="/games", tags=["assets"])


@router.post("/{game_id}/assets/presign", response_model=PresignAssetResponse)
def presign_asset(
    game_id: uuid.UUID,
    body: PresignAssetBody,
    session: SessionDep,
    user_id: UserIdDep,
    cos: CosDep,
    settings: SettingsDep,
) -> dict[str, Any]:
    return asset_service.presign_asset(
        owner_id=user_id,
        game_id=game_id,
        filename=body.filename,
        content_type=body.content_type,
        size=body.size,
        max_bytes=settings.asset_max_upload_bytes,
        expires_seconds=settings.asset_presign_expires_seconds,
        session=session,
        cos=cos,
    )


@router.post("/{game_id}/assets/{asset_id}/complete", response_model=AssetResponse)
def complete_asset(
    game_id: uuid.UUID,
    asset_id: uuid.UUID,
    body: CompleteAssetBody,
    session: SessionDep,
    user_id: UserIdDep,
    cos: CosDep,
    settings: SettingsDep,
) -> dict[str, Any]:
    return asset_service.complete_asset(
        owner_id=user_id,
        game_id=game_id,
        asset_id=asset_id,
        filename=body.filename,
        max_bytes=settings.asset_max_upload_bytes,
        session=session,
        cos=cos,
    )


@router.get("/{game_id}/assets", response_model=list[AssetListItem])
def list_assets(
    game_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
    cos: CosDep,
) -> list[dict[str, Any]]:
    return asset_service.list_assets(
        owner_id=user_id, game_id=game_id, session=session, cos=cos
    )


@router.delete("/{game_id}/assets/{asset_id}", status_code=204)
def delete_asset(
    game_id: uuid.UUID,
    asset_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
    cos: CosDep,
) -> None:
    asset_service.delete_asset(
        owner_id=user_id, game_id=game_id, asset_id=asset_id, session=session, cos=cos
    )
