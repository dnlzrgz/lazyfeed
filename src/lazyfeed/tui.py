import asyncio
from pathlib import Path
import aiohttp
import click
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from lazyfeed.config import Settings
from lazyfeed.db import init_db
from lazyfeed.feeds import fetch_feed
from lazyfeed.help_modal import HelpModal
from lazyfeed.models import Post
from lazyfeed.tabloid import Tabloid
from lazyfeed.repositories import FeedRepository, PostRepository


class LazyFeedApp(App):
    """
    A Textual based application to read RSS feeds in
    the terminal.
    """

    TITLE = "lazyfeed"
    CSS_PATH = "global.tcss"

    BINDINGS = [
        Binding("?", "display_help", "Display Help Message", show=False),
        Binding("q", "quit", "Quit", show=False),
        Binding("escape", "quit", "Quit", show=False),
        Binding("r", "reload", "Reload", show=False),
    ]

    def __init__(self, session: Session, _: Settings, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._session = session
        self.feeds_repository = FeedRepository(self._session)
        self.post_repository = PostRepository(self._session)

    def compose(self) -> ComposeResult:
        yield Tabloid()

    def action_display_help(self) -> None:
        self.push_screen(HelpModal())

    def action_reload(self) -> None:
        self.tabloid.loading = True
        self.tabloid.clear()
        self.load_new_posts()

    def on_mount(self) -> None:
        self.tabloid = self.query_one(Tabloid)

    async def on_quit(self) -> None:
        self._session.flush()
        self.app.exit()

    @on(Tabloid.Ready)
    async def start_fetching(self) -> None:
        self.tabloid.loading = True
        self.load_new_posts()

    @on(Tabloid.OpenItem)
    def open_item(self, message: Tabloid.OpenItem) -> None:
        post_in_db = self.post_repository.get(message.post_id)
        if not post_in_db:
            self.notify(
                "Unable to open the selected item",
                severity="error",
            )
            return

        self.open_url(post_in_db.url)
        self.post_repository.update(message.post_id, read=True)

    @on(Tabloid.MarkItemAsRead)
    def mark_item_as_read(self, message: Tabloid.MarkItemAsRead) -> None:
        self.post_repository.update(message.post_id, read=True)

    @on(Tabloid.MarkAllItemsAsRead)
    def mark_all_items_as_read(self) -> None:
        self.tabloid.loading = True

        try:
            self.post_repository.mark_all_as_read()
            self.notify(
                "All items have been marked as read",
                severity="information",
            )
        except Exception:
            self.notify(
                "Something went wrong while marking all items as read!",
                severity="error",
            )
        finally:
            self.tabloid.loading = False

    @work(exclusive=True)
    async def load_new_posts(self) -> None:
        feeds = self.feeds_repository.get_all()
        if not len(feeds):
            self.notify(
                "You need to add some feeds first!",
                severity="warning",
            )
            self.tabloid.loading = False
            return

        async with aiohttp.ClientSession() as client:
            tasks = [fetch_feed(client, feed) for feed in feeds]
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

                new_entries = []
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

                    new_entries.append(
                        Post(
                            feed=feed,
                            url=entry_link,
                            title=entry_title,
                            summary=entry_summary,
                        )
                    )

                self.post_repository.add_in_batch(new_entries)

        pending_posts = self.post_repository.get_by_attributes(read=False)

        self.tabloid.loading = False
        self.tabloid.focus()

        for post in pending_posts:
            label = f"[bold][{post.feed.title}][/bold] {post.title}"
            self.tabloid.add_row(label, key=f"{post.id}")

        self.notify(f"{len(pending_posts)} new posts!")


if __name__ == "__main__":
    app_dir = Path(click.get_app_dir(app_name="lazyfeed"))
    app_dir.mkdir(parents=True, exist_ok=True)

    sqlite_url = f"sqlite:///{app_dir / 'lazyfeed.db'}"
    engine = create_engine(sqlite_url)
    init_db(engine)

    with Session(engine) as session:
        app = LazyFeedApp(session, Settings())
        app.run()
