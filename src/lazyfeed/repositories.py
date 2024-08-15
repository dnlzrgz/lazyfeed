from sqlalchemy import update
from sqlalchemy.orm import Session
from lazyfeed.models import Feed, Post


class Repository[T: (Feed, Post)]:
    def __init__(self, session: Session, model: T) -> None:
        self.session = session
        self.model = model

    def add(self, entity: T) -> T:
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)

        return entity

    def get(self, id: int) -> T | None:
        return self.session.get(self.model, id)

    def get_by_attributes(self, **kwargs) -> list[T] | None:
        return self.session.query(self.model).filter_by(**kwargs).all()

    def get_all(self) -> list[T]:
        return self.session.query(self.model).all()

    def update(self, id: int, **kwargs) -> None:
        stmt = update(self.model).where(self.model.id == id).values(**kwargs)
        self.session.execute(stmt)
        self.session.commit()

    def delete(self, id: int) -> None:
        entity = self.session.get(self.model, id)
        if entity:
            self.session.delete(entity)
            self.session.commit()


class FeedRepository(Repository[Feed]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Feed)


class PostRepository(Repository[Post]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Post)
