import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy import func, select, text, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.core.constants import (
    PUBLISH_JOB_TTL_SECONDS,
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

    def acquire_publish_lock(self, session: Session, *, game_id: uuid.UUID) -> bool:
        """尝试抢占本游戏的发布权（事务级咨询锁，commit/rollback 自动释放）。

        锁只保护「检查在途版本 → 分配 seq → 插入 deploying 版本」这一小段临界区，
        不覆盖整段部署；跨进程/多实例互斥由 deploying 状态行承担。
        """
        acquired = session.scalar(
            text("SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"publish:{game_id}"},
        )
        return bool(acquired)

    def active_for_game(self, session: Session, game_id: uuid.UUID) -> GameVersion | None:
        """本游戏当前在途（deploying）的版本。"""
        return session.scalar(
            select(GameVersion)
            .where(
                GameVersion.game_id == game_id,
                GameVersion.status == VERSION_STATUS_DEPLOYING,
            )
            .order_by(GameVersion.seq.desc())
            .limit(1)
        )

    def fail_stale_for_game(self, session: Session, *, game_id: uuid.UUID) -> int:
        """把超过 TTL 仍卡在 deploying 的版本标记为 failed（不提交事务）。"""
        cutoff = datetime.now(UTC) - timedelta(seconds=PUBLISH_JOB_TTL_SECONDS)
        result = cast(
            CursorResult[tuple[object, ...]],
            session.execute(
                update(GameVersion)
                .where(
                    GameVersion.game_id == game_id,
                    GameVersion.status == VERSION_STATUS_DEPLOYING,
                    GameVersion.created_at < cutoff,
                )
                .values(status=VERSION_STATUS_FAILED)
                .execution_options(synchronize_session=False)
            ),
        )
        return int(result.rowcount or 0)

    def reap_stale(self, session: Session, *, game_id: uuid.UUID) -> int:
        """回收过期部署任务；有变更才提交。"""
        changed = self.fail_stale_for_game(session, game_id=game_id)
        if changed:
            session.commit()
        return changed

    def fail_all_deploying(self, session: Session) -> int:
        """启动对账：进程内执行器不持久，重启后残留的 deploying 一律判失败。"""
        result = cast(
            CursorResult[tuple[object, ...]],
            session.execute(
                update(GameVersion)
                .where(GameVersion.status == VERSION_STATUS_DEPLOYING)
                .values(status=VERSION_STATUS_FAILED)
                .execution_options(synchronize_session=False)
            ),
        )
        session.commit()
        return int(result.rowcount or 0)

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
            game_id=game_id,
            seq=seq,
            source_thread_id=source_thread_id,
            note=note,
            status=VERSION_STATUS_DEPLOYING,
        )
        session.add(version)
        session.commit()
        session.refresh(version)
        return version

    def get(self, session: Session, version_id: uuid.UUID) -> GameVersion | None:
        return session.get(GameVersion, version_id)

    def latest_for_game(self, session: Session, game_id: uuid.UUID) -> GameVersion | None:
        return session.scalar(
            select(GameVersion)
            .where(GameVersion.game_id == game_id)
            .order_by(GameVersion.seq.desc())
            .limit(1)
        )

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
