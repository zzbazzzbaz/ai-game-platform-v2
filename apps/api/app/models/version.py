import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import PLATFORM_SCHEMA, VERSION_STATUS_DEPLOYING
from app.core.database import Base


class GameVersion(Base):
    __tablename__ = "game_versions"
    __table_args__ = (
        UniqueConstraint("game_id", "seq", name="uq_game_versions_game_seq"),
        {"schema": PLATFORM_SCHEMA},
    )

    version_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{PLATFORM_SCHEMA}.games.game_id"), nullable=False, index=True
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    source_thread_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{PLATFORM_SCHEMA}.game_threads.thread_id"), nullable=False
    )
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default=VERSION_STATUS_DEPLOYING
    )
    revision: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
