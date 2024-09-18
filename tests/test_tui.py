import asyncio
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from lazyfeed.db import init_db
from lazyfeed.models import Feed, Post
from lazyfeed.repositories import FeedRepository, PostRepository
from lazyfeed.settings import Settings
from lazyfeed.tui import ActiveView, LazyFeedApp


@pytest.fixture(scope="function")
def settings():
    settings = Settings()
    settings.app.db_url = "sqlite:///:memory:"
    return settings


@pytest.fixture(scope="function")
def session(settings):
    engine = create_engine(settings.app.db_url)
    init_db(engine)
    session = Session(engine)

    yield session

    session.close()


def _populate_db(session) -> int:
    feed_repo = FeedRepository(session)
    feed = feed_repo.add(
        Feed(
            url="http://hitchhikers.com/rss",
            title="The Hitchhiker's Guide to the Galaxy",
            link="http://hitchhikers.com",
            description="A guide to the galaxy, filled with useful information and humor.",
        )
    )

    post_repo = PostRepository(session)
    posts = [
        Post(
            feed_id=feed.id,
            url="http://hitchhikers.com/item1",
            author="Douglas Adams",
            title="Don't Panic",
            summary="The most important phrase in the universe.",
            content="Always know where your towel is.",
        ),
        Post(
            feed_id=feed.id,
            url="http://hitchhikers.com/item2",
            author="Douglas Adams",
            title="The Answer to Life, the Universe, and Everything",
            summary="The number 42.",
            content="The answer to the ultimate question of life, the universe, and everything is 42.",
        ),
        Post(
            feed_id=feed.id,
            url="http://hitchhikers.com/item3",
            author="Douglas Adams",
            title="The Hitchhiker's Guide",
            summary="A book that tells you everything you need to know.",
            content="A guide that provides information about the galaxy.",
        ),
        Post(
            feed_id=feed.id,
            url="http://hitchhikers.com/item4",
            author="Douglas Adams",
            title="The Infinite Improbability Drive",
            summary="A drive that allows for improbable events.",
            content="A drive that makes the impossible possible.",
        ),
    ]

    for post in posts:
        post_repo.add(post)

    return len(posts)


async def test_views(settings, session):
    app = LazyFeedApp(session, settings)

    async with app.run_test() as pilot:
        assert app.tabloid.border_title == "lazyfeed"
        assert app.active_view == ActiveView.IDLE

        await pilot.press("g", "l")
        assert app.tabloid.border_title == "lazyfeed/saved"
        assert app.active_view == ActiveView.SAVED

        await pilot.press("g", "a")
        assert app.tabloid.border_title == "lazyfeed/all"
        assert app.active_view == ActiveView.ALL

        await pilot.press("g", "f")
        assert app.tabloid.border_title == "lazyfeed/fav"
        assert app.active_view == ActiveView.FAV

        await pilot.press("g", "p")
        assert app.tabloid.border_title == "lazyfeed"
        assert app.active_view == ActiveView.PENDING


async def test_mark_item_as_read(settings, session):
    num_posts = _populate_db(session)

    settings.app.show_read = False
    app = LazyFeedApp(session, settings)

    async with app.run_test() as pilot:
        await asyncio.sleep(1)
        assert app.tabloid.row_count == num_posts

        await pilot.press("m")
        assert app.tabloid.row_count == num_posts - 1


async def test_mark_all_items_as_read(settings, session):
    num_posts = _populate_db(session)

    settings.app.show_read = False
    app = LazyFeedApp(session, settings)

    async with app.run_test() as pilot:
        await asyncio.sleep(1)
        assert app.tabloid.row_count == num_posts

        await pilot.press("A")
        assert app.tabloid.row_count == 0
