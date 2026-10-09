import time

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.game import Game


class GameRepository:
    def upsert(
        self,
        session: Session,
        *,
        game_id: str,
        thread_id: str,
        user_id: str,
        name: str,
        game_type: str,
    ) -> None:
        now = int(time.time())
        session.execute(
            insert(Game)
            .values(
                game_id=game_id,
                thread_id=thread_id,
                user_id=user_id,
                name=name,
                game_type=game_type,
                created_at=now,
                published_at=now,
            )
            .on_conflict_do_update(
                index_elements=["game_id"],
                set_={"name": name, "published_at": now},
            )
        )
        session.commit()


game_repository = GameRepository()
