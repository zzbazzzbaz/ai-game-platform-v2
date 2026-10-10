import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import (
    VERSION_STATUS_DEPLOYED,
    VERSION_STATUS_DEPLOYING,
    VERSION_STATUS_FAILED,
)
from app.models.version import GameVersion


class VersionRepository:
    def next_seq(self, session: Session, game_id: uuid.UUID) -> int:
        current = session.scalar(
            select(func.max(GameVersion.seq)).where(GameVersion.game_id == game_id)
        )
        return (current or 0) + 1

    def create(
        self,
        session: Session,
        *,
        game_id: uuid.UUID,
        seq: int,
        source_thread_id: uuid.UUID,
        note: str = "",
    ) -> GameVersion:
        version = GameVersion(
            game_id=game_id, seq=seq, source_thread_id=source_thread_id, note=note
        )
        session.add(version)
        session.commit()
        session.refresh(version)
        return version

    def list_by_game(self, session: Session, game_id: uuid.UUID) -> list[GameVersion]:
        return list(
            session.scalars(
                select(GameVersion)
                .where(GameVersion.game_id == game_id)
                .order_by(GameVersion.seq.desc())
            )
        )

    def current_deployed(self, session: Session, game_id: uuid.UUID) -> GameVersion | None:
        return session.scalar(
            select(GameVersion)
            .where(GameVersion.game_id == game_id, GameVersion.status == VERSION_STATUS_DEPLOYED)
            .order_by(GameVersion.seq.desc())
            .limit(1)
        )

    def mark_deploying(self, session: Session, version_id: uuid.UUID) -> None:
        version = session.get(GameVersion, version_id)
        if version is not None:
            version.status = VERSION_STATUS_DEPLOYING
            session.commit()

    def mark_deployed(
        self, session: Session, version_id: uuid.UUID, *, revision: str | None
    ) -> None:
        version = session.get(GameVersion, version_id)
        if version is not None:
            version.status = VERSION_STATUS_DEPLOYED
            version.revision = revision
            version.deployed_at = datetime.now(UTC)
            session.commit()

    def mark_failed(self, session: Session, version_id: uuid.UUID) -> None:
        version = session.get(GameVersion, version_id)
        if version is not None:
            version.status = VERSION_STATUS_FAILED
            session.commit()


version_repository = VersionRepository()
