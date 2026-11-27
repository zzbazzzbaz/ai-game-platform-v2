import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.map import GameMap


class MapRepository:
    def list_ids(self, session: Session, game_id: uuid.UUID) -> list[str]:
        """按创建时间升序返回图 id；同一时间按 map_id 升序。"""
        return list(
            session.scalars(
                select(GameMap.map_id)
                .where(GameMap.game_id == game_id)
                .order_by(GameMap.created_at.asc(), GameMap.map_id.asc())
            )
        )

    def get(self, session: Session, *, game_id: uuid.UUID, map_id: str) -> GameMap | None:
        return session.get(GameMap, (game_id, map_id))

    def upsert(
        self,
        session: Session,
        *,
        game_id: uuid.UUID,
        map_id: str,
        content: dict[str, object],
    ) -> GameMap:
        """整张覆盖保存：新建 revision=1，已存在则 revision+1 并刷新 updated_at。"""
        statement = (
            insert(GameMap)
            .values(game_id=game_id, map_id=map_id, content=content, revision=1)
            .on_conflict_do_update(
                index_elements=[GameMap.game_id, GameMap.map_id],
                set_={
                    "content": content,
                    "revision": GameMap.revision + 1,
                    "updated_at": func.now(),
                },
            )
            .returning(GameMap)
        )
        game_map = session.scalars(statement).one()
        session.commit()
        return game_map


map_repository = MapRepository()
