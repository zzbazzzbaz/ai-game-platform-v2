import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import PLATFORM_SCHEMA
from app.core.database import Base


class GameMap(Base):
    """玩法图：属于游戏，按 (game_id, map_id) 整张覆盖保存。"""

    __tablename__ = "game_maps"
    __table_args__ = {"schema": PLATFORM_SCHEMA}

    game_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{PLATFORM_SCHEMA}.games.game_id", ondelete="CASCADE"),
        primary_key=True,
    )
    map_id: Mapped[str] = mapped_column(Text, primary_key=True)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
