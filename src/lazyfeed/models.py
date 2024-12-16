from datetime import datetime
from typing import List
from sqlalchemy import ForeignKey, Boolean, Text, func
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


class Feed(Base):
    __tablename__ = "feed"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(unique=True)
    site: Mapped[str] = mapped_column(nullable=True)
    title: Mapped[str]
    description: Mapped[str] = mapped_column(nullable=True)

    items: Mapped[List["Item"]] = relationship(
        back_populates="feed",
        cascade="all, delete",
    )

    etag: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    last_updated_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Feed(id={self.id!r}, url={self.url!r}, site={self.site!r}, title={self.title!r}, created_at={self.created_at!r}, last_updated_at={self.last_updated_at!r})>"


class Item(Base):
    __tablename__ = "item"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(nullable=True)
    url: Mapped[str] = mapped_column(unique=True)
    author: Mapped[str] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean(), default=False)
    is_saved: Mapped[bool] = mapped_column(Boolean(), default=False)

    feed_id: Mapped[int] = mapped_column(ForeignKey("feed.id"))
    feed: Mapped[Feed] = relationship(back_populates="items")

    raw_content: Mapped[str] = mapped_column(Text(), nullable=True)
    content: Mapped[str] = mapped_column(Text(), nullable=True)

    published_at: Mapped[datetime] = mapped_column(default=func.now())
    last_updated_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Item(id={self.id!r}, url={self.url!r}, author={self.author!r}, title={self.title!r}, is_read={self.is_read!r}, is_favorite={self.is_favorite!r}, is_saved={self.is_saved!r}, published_at={self.published_at!r}, last_updated_at={self.last_updated_at!r})>"
