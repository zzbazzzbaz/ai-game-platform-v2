import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.thread import GameThread


class ThreadRepository:
    def create(self, session: Session, *, game_id: uuid.UUID, title: str = "") -> GameThread:
        thread = GameThread(game_id=game_id, title=title)
        session.add(thread)
        session.commit()
        session.refresh(thread)
        return thread

    def list_by_game(self, session: Session, game_id: uuid.UUID) -> list[GameThread]:
        return list(
            session.scalars(
                select(GameThread)
                .where(GameThread.game_id == game_id)
                .order_by(GameThread.created_at.asc())
            )
        )

    def get(self, session: Session, thread_id: uuid.UUID) -> GameThread | None:
        return session.get(GameThread, thread_id)


thread_repository = ThreadRepository()
