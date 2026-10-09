from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Game(Base):
    __tablename__ = "games"

    # 本期无多版本（D5）：game_id = thread_id，覆盖式发布
    game_id: Mapped[str] = mapped_column(Text, primary_key=True)
    thread_id: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    game_type: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    published_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
