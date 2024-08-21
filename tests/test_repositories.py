import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from lazyfeed.repositories import FeedRepository, PostRepository
from lazyfeed.models import Base, Feed


@pytest.fixture(scope="function")
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture
def feed_repository(session):
    return FeedRepository(session)


@pytest.fixture
def posts_repository(session):
    return PostRepository(session)


class TestFeedRepository:
    @pytest.fixture(autouse=True)
    def setup(self, feed_repository):
        self.feed_repository = feed_repository
        self.feed = Feed(
            url="https://dontpanic.com/feed",
            title="The Infinite Improbability Newsfeed",
        )

    def test_add(self):
        assert self.feed.id is None

        feed_in_db = self.feed_repository.add(self.feed)
        assert feed_in_db.id is not None
        assert feed_in_db.created_at is not None
        assert feed_in_db.last_updated_at is not None
        assert feed_in_db.id == 1
        assert feed_in_db.title == self.feed.title
        assert feed_in_db.url == self.feed.url

    def test_get(self):
        feed_in_db = self.feed_repository.get(1)
        assert feed_in_db is None

        self.feed_repository.add(self.feed)

        feed_in_db = self.feed_repository.get(1)
        assert feed_in_db is not None
        assert feed_in_db.url == self.feed.url
        assert feed_in_db.title == self.feed.title

    def test_get_by_attributes(self):
        feeds_in_db = self.feed_repository.get_by_attributes(title=self.feed.title)
        assert len(feeds_in_db) == 0

        self.feed_repository.add(self.feed)

        feeds_in_db = self.feed_repository.get_by_attributes(title=self.feed.title)
        assert len(feeds_in_db) == 1
        assert feeds_in_db[0].title == self.feed.title

    def test_get_all(self):
        for i in range(5):
            self.feed_repository.add(
                Feed(
                    title=f"https://news.{ i + 1}.com/rss",
                    url=f"News {i + 1}",
                )
            )

        feeds_in_db = self.feed_repository.get_all()
        assert len(feeds_in_db) == 5

    def test_update(self):
        original_feed = self.feed_repository.add(self.feed)
        original_feed_title = self.feed.title
        self.feed_repository.update(
            original_feed.id,
            title="The Finite Certainty Bulletin",
        )

        updated_feed = self.feed_repository.get(original_feed.id)
        assert updated_feed is not None
        assert updated_feed.title != original_feed_title

    def test_delete(self):
        feed_in_db = self.feed_repository.add(self.feed)
        assert feed_in_db is not None

        self.feed_repository.delete(feed_in_db.id)
        deleted_feed = self.feed_repository.get(feed_in_db.id)
        assert deleted_feed is None
