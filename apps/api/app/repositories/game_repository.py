import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.game import Game


class GameRepository:
    def create(self, session: Session, *, owner_id: uuid.UUID, name: str) -> Game:
        game = Game(owner_id=owner_id, name=name)
        session.add(game)
        session.commit()
        session.refresh(game)
        return game

    def list_by_owner(self, session: Session, owner_id: uuid.UUID) -> list[Game]:
        return list(
            session.scalars(
                select(Game).where(Game.owner_id == owner_id).order_by(Game.created_at.desc())
            )
        )

    def get(self, session: Session, game_id: uuid.UUID) -> Game | None:
        return session.get(Game, game_id)

    def set_sandbox_id(self, session: Session, *, game_id: uuid.UUID, sandbox_id: str) -> None:
        game = session.get(Game, game_id)
        if game is not None:
            game.sandbox_id = sandbox_id
            session.commit()

    def set_public_url(self, session: Session, *, game_id: uuid.UUID, public_url: str) -> None:
        game = session.get(Game, game_id)
        if game is not None:
            game.public_url = public_url
            session.commit()


game_repository = GameRepository()
