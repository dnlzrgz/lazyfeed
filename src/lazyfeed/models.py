from datetime import datetime, timezone
from typing import List
from sqlalchemy import ForeignKey, Boolean, Text
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


class Feed(Base):
    __tablename__ = "feeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(unique=True, index=True)
    link: Mapped[str] = mapped_column(nullable=True)
    title: Mapped[str]
    description: Mapped[str] = mapped_column(nullable=True)
    posts: Mapped[List["Post"]] = relationship(
        back_populates="feed",
        cascade="all, delete",
        passive_deletes=True,
    )

    etag: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc))
    last_updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"Feed(id={self.id!r}, url={self.url!r}, title={self.title!r}, created_at={self.created_at!r}, last_updated_at={self.last_updated_at!r})"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    feed_id: Mapped[int] = mapped_column(ForeignKey("feeds.id"))
    feed: Mapped[Feed] = relationship(back_populates="posts")
    url: Mapped[str] = mapped_column(unique=True, index=True)
    author: Mapped[str] = mapped_column(nullable=True)
    title: Mapped[str]
    summary: Mapped[str] = mapped_column(nullable=True)
    content: Mapped[str] = mapped_column(Text(), nullable=True)

    read: Mapped[bool] = mapped_column(Boolean(), default=False)
    favorite: Mapped[bool] = mapped_column(Boolean(), default=False)
    saved_for_later: Mapped[bool] = mapped_column(Boolean(), default=False)

    published_at: Mapped[datetime] = mapped_column(
        default=datetime.now(timezone.utc),
        index=True,
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"Post(id={self.id!r}, url={self.url!r}, title={self.title!r}, favorite={self.favorite!r}, saved_for_later={self.saved_for_later!r}, published_at={self.published_at!r}, last_updated_at={self.last_updated_at!r})"
