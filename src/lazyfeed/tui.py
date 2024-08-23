import asyncio
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from textual import on, work
from textual.app import App, ComposeResult
from lazyfeed.db import init_db
from lazyfeed.feeds import fetch_feed
from lazyfeed.help_modal import HelpModal
from lazyfeed.models import Post
from lazyfeed.news_list import NewsList, NewsListItem
from lazyfeed.repositories import FeedRepository, PostRepository


class LazyFeedApp(App):
    """
    A Textual based application to read RSS feeds in
    the terminal.
    """

    TITLE = "lazyfeed"
    CSS_PATH = "global.tcss"

    BINDINGS = [
        ("?", "display_help", "Display Help Message"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, session: Session, client: httpx.AsyncClient, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._session = session
        self.feeds_repository = FeedRepository(self._session)
        self.post_repository = PostRepository(self._session)

        self.client = client

    def compose(self) -> ComposeResult:
        yield NewsList()

    def action_display_help(self) -> None:
        self.push_screen(HelpModal())

    def on_mount(self) -> None:
        self.news_list = self.query_one(NewsList)

    async def on_quit(self) -> None:
        await self.client.aclose()
        self._session.flush()
        self.app.exit()

    @on(NewsList.Ready)
    async def start_fetching(self) -> None:
        self.load_new_posts()

    @on(NewsList.MarkItemAsRead)
    def mark_item_as_readed(self, message: NewsList.MarkItemAsRead) -> None:
        self.post_repository.update(message.post_id, readed=True)

    @on(NewsList.MarkAllItemsAsRead)
    def mark_all_items_as_readed(self) -> None:
        pending_posts = self.post_repository.get_by_attributes(readed=False)
        for post in pending_posts:
            self.post_repository.update(post.id, readed=True)

        self.notify(
            "All items have been marked as read",
            severity="information",
        )

    @work()
    async def load_new_posts(self) -> None:
        feeds = self.feeds_repository.get_all()

        if not len(feeds):
            self.notify(
                "You need to add some feeds first!",
                severity="warning",
            )
            return

        tasks = [fetch_feed(self.client, feed) for feed in feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for feed, result in zip(feeds, results):
            if isinstance(result, Exception):
                self.notify(
                    f"Something bad happened while fetching '{feed.url}'",
                    severity="error",
                )
                continue

            entries, etag = result
            if etag:
                self.feeds_repository.update(feed.id, etag=etag)

            for entry in entries:
                posts_in_db = self.post_repository.get_by_attributes(url=entry.link)
                if posts_in_db:
                    continue

                entry_link = getattr(entry, "link", None)
                entry_title = getattr(entry, "title", None)
                entry_summary = getattr(entry, "summary", None)
                if not entry_link or not entry_title:
                    self.notify(
                        f"Something bad happened while fetching '{entry.title}'",
                        severity="error",
                    )
                    continue

                self.post_repository.add(
                    Post(
                        feed=feed,
                        url=entry_link,
                        title=entry_title,
                        summary=entry_summary,
                    )
                )

        pending_posts = self.post_repository.get_by_attributes(readed=False)
        items = [NewsListItem(post) for post in pending_posts]
        self.news_list.mount_all(items)

        self.notify(f"{len(items)} new posts!")


if __name__ == "__main__":
    engine = create_engine("sqlite:///lazyfeed.db")
    init_db(engine)

    client = httpx.AsyncClient(timeout=10, follow_redirects=True)
    with Session(engine) as session:
        app = LazyFeedApp(session, client)
        app.run()
