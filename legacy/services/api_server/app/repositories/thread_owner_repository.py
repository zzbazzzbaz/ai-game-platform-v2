import time

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.thread_owner import ThreadOwner


class ThreadOwnerRepository:
    def get(self, session: Session, thread_id: str) -> ThreadOwner | None:
        return session.get(ThreadOwner, thread_id)

    def claim(self, session: Session, thread_id: str, user_id: str) -> None:
        now = int(time.time())
        session.execute(
            insert(ThreadOwner)
            .values(thread_id=thread_id, user_id=user_id, created_at=now, updated_at=now)
            .on_conflict_do_nothing(index_elements=["thread_id"])
        )
        session.commit()


thread_owner_repository = ThreadOwnerRepository()
