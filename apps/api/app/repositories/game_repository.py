import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.game import Game


class GameRepository:
    def create(
        self,
        session: Session,
        *,
        owner_id: uuid.UUID,
        name: str,
        game_id: uuid.UUID | None = None,
    ) -> Game:
        game = Game(owner_id=owner_id, name=name)
        if game_id is not None:
            game.game_id = game_id
        session.add(game)
        session.commit()
        session.refresh(game)
        return game

    def list_by_owner(self, session: Session, owner_id: uuid.UUID) -> list[Game]:
        return list(
            session.scalars(
                select(Game)
                .where(Game.owner_id == owner_id)
                .order_by(Game.updated_at.desc())
            )
        )

    def get(self, session: Session, game_id: uuid.UUID) -> Game | None:
        return session.get(Game, game_id)

    def lock(self, session: Session, *, game_id: uuid.UUID) -> Game | None:
        """按 game_id 对 games 行加行锁（SELECT ... FOR UPDATE），返回锁内最新值。

        用途：把同一游戏的沙盒开通（ensure）串行化，避免并发请求各建一个沙盒。
        行锁一直持有到当前事务 commit/rollback，因此调用方必须让「读 sandbox_id →
        创建/复用沙盒 → 写 sandbox_id」处在同一事务内。

        - `with_for_update=True`：对象已在 identity map 时普通 `session.get` 不会发 SQL
          （等于没加锁），带上它才会发出 `... FOR UPDATE`；
        - `populate_existing=True`：强制用锁到的那一行刷新属性，避免读到更早的缓存值。
        """
        return session.get(Game, game_id, with_for_update=True, populate_existing=True)

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
