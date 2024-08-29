import asyncio
from enum import Enum
from pathlib import Path
import aiohttp
import click
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from lazyfeed.config import Settings
from lazyfeed.db import init_db
from lazyfeed.feeds import fetch_feed
from lazyfeed.help_modal import HelpModal
from lazyfeed.models import Post
from lazyfeed.repositories import FeedRepository, PostRepository
from lazyfeed.tabloid import Tabloid

ActiveView = Enum("ActiveView", ["START", "ALL", "PENDING", "SAVED", "FAV"])


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
        Binding("r", "refresh", "Reload", show=False),
    ]

    active_view: reactive[ActiveView] = reactive(ActiveView.START)

    def __init__(self, session: Session, _: Settings, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._session = session
        self.feeds_repository = FeedRepository(self._session)
        self.post_repository = PostRepository(self._session)

    def compose(self) -> ComposeResult:
        yield Tabloid()

    def action_display_help(self) -> None:
        self.push_screen(HelpModal())

    def action_refresh(self) -> None:
        self.fetch_new_posts()

    async def on_mount(self) -> None:
        self.tabloid = self.query_one(Tabloid)
        self.fetch_new_posts()

    async def on_quit(self) -> None:
        self._session.flush()
        self.app.exit()

    @on(Tabloid.RefreshPosts)
    async def start_fetching(self) -> None:
        self.fetch_new_posts()

    @on(Tabloid.LoadAllPosts)
    async def set_view_to_pending(self) -> None:
        self.active_view = ActiveView.PENDING

    @on(Tabloid.LoadSavedPosts)
    async def set_view_to_saved(self) -> None:
        self.active_view = ActiveView.SAVED

    @on(Tabloid.LoadFavPosts)
    async def set_view_to_fav(self) -> None:
        self.active_view = ActiveView.FAV

    @on(Tabloid.OpenPost)
    def open_item(self, message: Tabloid.OpenPost) -> None:
        post_in_db = self.post_repository.get(message.post_id)
        if not post_in_db:
            self.notify(
                "Unable to open the selected item",
                severity="error",
            )
            return

        self.open_url(post_in_db.url)

        if post_in_db.favorite and self.active_view == ActiveView.FAV:
            self.post_repository.update(message.post_id, read=True)
            self.tabloid.update_cell(
                f"{post_in_db.id}",
                "title",
                self._gen_row_content(post_in_db)[2],
            )
            return
        elif post_in_db.saved_for_later and self.active_view == ActiveView.SAVED:
            self.post_repository.update(
                message.post_id, read=True, saved_for_later=False
            )
            self.tabloid.update_cell(
                f"{post_in_db.id}",
                "title",
                self._gen_row_content(post_in_db)[2],
            )
            return
        else:
            self.post_repository.update(message.post_id, read=True)
            self.tabloid.remove_row(f"{post_in_db.id}")

    @on(Tabloid.SavePost)
    def save_for_later(self, message: Tabloid.SavePost) -> None:
        post_in_db = self.post_repository.get(message.post_id)
        if not post_in_db:
            self.notify(
                "Unable to save for later the selected item",
                severity="error",
            )
            return

        self.post_repository.update(
            message.post_id, saved_for_later=not post_in_db.saved_for_later
        )

        saved = "\uf02e" if post_in_db.saved_for_later else ""
        self.tabloid.update_cell(f"{message.post_id}", "saved", saved)

    @on(Tabloid.MarkPostAsFav)
    def mark_as_fav(self, message: Tabloid.MarkPostAsFav) -> None:
        post_in_db = self.post_repository.get(message.post_id)
        if not post_in_db:
            self.notify(
                "Unable to mark as fav the selected item",
                severity="error",
            )
            return

        self.post_repository.update(message.post_id, favorite=not post_in_db.favorite)

        fav = "\uf005" if post_in_db.favorite else ""
        self.tabloid.update_cell(f"{post_in_db.id}", "fav", fav)

    @on(Tabloid.MarkPostAsRead)
    def mark_item_as_read(self, message: Tabloid.MarkPostAsRead) -> None:
        post_in_db = self.post_repository.get(message.post_id)
        if not post_in_db:
            self.notify(
                "Unable to mark as read the selected item",
                severity="error",
            )
            return

        if message.pop:
            self.post_repository.update(post_in_db.id, read=True)
            self.tabloid.remove_row(f"{post_in_db.id}")
        else:
            if post_in_db.read:
                self.post_repository.update(post_in_db.id, read=False)
            else:
                self.post_repository.update(
                    post_in_db.id, read=True, saved_for_later=False
                )

            self.tabloid.update_cell(
                f"{post_in_db.id}",
                "title",
                self._gen_row_content(post_in_db)[2],
            )

    @on(Tabloid.MarkAllPostsAsRead)
    def mark_all_items_as_read(self) -> None:
        self.tabloid.loading = True

        try:
            self.post_repository.mark_all_as_read()
            self.active_view = ActiveView.PENDING
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

    def watch_active_view(self, old_view: ActiveView, new_view: ActiveView) -> None:
        if old_view == new_view:
            return

        if new_view == ActiveView.PENDING:
            self.tabloid.border_title = "lazyfeed"
            self._load_pending_posts()
            return

        if new_view == ActiveView.SAVED:
            self.tabloid.border_title = "lazyfeed/saved"
            self._load_saved_posts()
            return

        if new_view == ActiveView.FAV:
            self.tabloid.border_title = "lazyfeed/fav"
            self._load_fav_posts()

    def _gen_row_content(self, post: Post) -> tuple[str, str, str]:
        """Generate the row content for a given post."""
        saved = "\uf02e" if post.saved_for_later else ""
        fav = "\uf005" if post.favorite else ""
        label = f"[bold][{post.feed.title}][/bold] {post.title}"
        if post.read:
            label = f"[strike]{label}[/]"

        return saved, fav, label

    def _load_pending_posts(self) -> None:
        self.tabloid.clear()
        pending_posts = self.post_repository.get_by_attributes(read=False)
        for post in pending_posts:
            self.tabloid.add_row(*self._gen_row_content(post), key=f"{post.id}")

    def _load_saved_posts(self) -> None:
        self.tabloid.clear()
        saved_for_later = self.post_repository.get_by_attributes(saved_for_later=True)
        for post in saved_for_later:
            self.tabloid.add_row(*self._gen_row_content(post), key=f"{post.id}")

    def _load_fav_posts(self) -> None:
        self.tabloid.clear()
        fav_posts = self.post_repository.get_by_attributes(favorite=True)
        for post in fav_posts:
            self.tabloid.add_row(*self._gen_row_content(post), key=f"{post.id}")

    @work(exclusive=True)
    async def fetch_new_posts(self) -> None:
        self.tabloid.loading = True

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

                new_entries = []
                entries, etag = result
                if etag:
                    self.feeds_repository.update(feed.id, etag=etag)

                for entry in entries:
                    posts_in_db = self.post_repository.get_by_attributes(url=entry.link)
                    if posts_in_db:
                        continue

                    entry_link = entry.get("link", None)
                    entry_title = entry.get("title", None)
                    entry_summary = entry.get("summary", None)
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

        self.active_view = ActiveView.PENDING
        self.tabloid.loading = False
        self.tabloid.focus()


if __name__ == "__main__":
    app_dir = Path(click.get_app_dir(app_name="lazyfeed"))
    app_dir.mkdir(parents=True, exist_ok=True)

    sqlite_url = f"sqlite:///{app_dir / 'lazyfeed.db'}"
    engine = create_engine(sqlite_url)
    init_db(engine)

    with Session(engine) as session:
        app = LazyFeedApp(session, Settings())
        app.run()
