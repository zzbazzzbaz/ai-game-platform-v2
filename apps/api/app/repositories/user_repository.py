import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def get(self, session: Session, user_id: uuid.UUID) -> User | None:
        return session.get(User, user_id)

    def get_by_username(self, session: Session, username: str) -> User | None:
        return session.scalar(select(User).where(User.username == username))

    def create(self, session: Session, *, username: str, password_hash: str) -> User:
        user = User(username=username, password_hash=password_hash)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


user_repository = UserRepository()
