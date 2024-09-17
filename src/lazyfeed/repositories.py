from sqlalchemy import select, update
from sqlalchemy.orm import Session
from lazyfeed.models import Feed, Post


class Repository[T: (Feed, Post)]:
    def __init__(self, session: Session, model) -> None:
        self.session = session
        self.model = model

    def add(self, entity: T) -> T:
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)

        return entity

    def add_in_batch(self, entities: list[T]) -> None:
        self.session.add_all(entities)
        self.session.commit()

    def get(self, id: int) -> T | None:
        stmt = select(self.model).where(self.model.id == id)
        return self.session.scalars(stmt).one_or_none()

    def get_by_attributes(self, **kwargs) -> list[T]:
        return self.session.query(self.model).filter_by(**kwargs).all()

    def get_all(self) -> list[T]:
        return self.session.query(self.model).all()

    def update(self, id: int, **kwargs) -> None:
        stmt = update(self.model).where(self.model.id == id).values(**kwargs)
        self.session.execute(stmt)
        self.session.commit()

    def delete(self, id: int) -> None:
        stmt = select(self.model).where(self.model.id == id)
        entity = self.session.scalars(stmt).one_or_none()
        if entity:
            self.session.delete(entity)
            self.session.commit()
            return entity


class FeedRepository(Repository[Feed]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Feed)


class PostRepository(Repository[Post]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Post)

    def get_sorted(self, sort_by: str, ascending: bool, **kwargs) -> list[Post]:
        sort_mapping = {
            "title": Post.title,
            "published_date": Post.published_at,
            "read_status": Post.read,
        }

        sort_criteria = sort_mapping.get(sort_by, Post.published_at)
        sort_order = sort_criteria.asc() if ascending else sort_criteria.desc()

        return self.session.query(Post).order_by(sort_order).filter_by(**kwargs).all()

    def mark_all_as_read(self) -> None:
        stmt = update(Post).where(Post.read == False).values(read=True)
        self.session.execute(stmt)
        self.session.commit()
