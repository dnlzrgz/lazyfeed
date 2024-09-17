import asyncio
from datetime import datetime, timezone
from enum import Enum
import aiohttp
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from lazyfeed.confirm_modal import ConfirmModal
from lazyfeed.db import init_db
from lazyfeed.feeds import fetch_feed
from lazyfeed.help_modal import HelpModal
from lazyfeed.models import Post
from lazyfeed.repositories import FeedRepository, PostRepository
from lazyfeed.settings import Settings
from lazyfeed.tabloid import Tabloid

ActiveView = Enum("ActiveView", ["IDLE", "ALL", "PENDING", "SAVED", "FAV"])


class LazyFeedApp(App):
    """
    A Textual based application to read RSS feeds in
    the terminal.
    """

    TITLE = "lazyfeed"
    CSS_PATH = "global.tcss"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("?", "display_help", "Display Help Message", show=False),
        Binding("q", "quit", "Quit", show=False),
        Binding("escape", "quit", "Quit", show=False),
        Binding("r", "refresh", "Reload", show=False),
    ]

    active_view: reactive[ActiveView] = reactive(ActiveView.IDLE)

    def __init__(self, session: Session, settings: Settings, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._session = session
        self._settings = settings
        self.feeds_repository = FeedRepository(self._session)
        self.post_repository = PostRepository(self._session)

    def compose(self) -> ComposeResult:
        yield Tabloid()

    def action_display_help(self) -> None:
        self.push_screen(HelpModal())

    def action_refresh(self) -> None:
        self.fetch_new_posts()

    async def action_quit(self) -> None:
        if self._settings.app.auto_mark_as_read:
            self.post_repository.mark_all_as_read()

        self._session.flush()
        self.app.exit()

    async def on_mount(self) -> None:
        self.tabloid = self.query_one(Tabloid)
        self.fetch_new_posts()

    @on(Tabloid.LoadAllPosts)
    async def set_view_to_all(self) -> None:
        self.active_view = ActiveView.ALL

    @on(Tabloid.LoadAllNewPosts)
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
        self.post_repository.update(message.post_id, read=True)
        row_removed = self._pop_post(f"{post_in_db.id}")

        if not row_removed:
            self.tabloid.update_cell(
                f"{post_in_db.id}",
                "title",
                self._gen_row_content(post_in_db)[2],
            )

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

        self.post_repository.update(message.post_id, read=not post_in_db.read)
        row_removed = self._pop_post(f"{post_in_db.id}")
        if row_removed:
            return

        self.tabloid.update_cell(
            f"{post_in_db.id}",
            "title",
            self._gen_row_content(post_in_db)[2],
        )

    @on(Tabloid.MarkAllPostsAsRead)
    def mark_all_items_as_read(self) -> None:
        def check_confirmation(response: bool | None) -> None:
            if response:
                self._mark_all_post_as_read()

        if self._settings.app.ask_before_marking_as_read:
            self.push_screen(
                ConfirmModal("Are you sure that you want to mark all items as read?"),
                check_confirmation,
            )
        else:
            self._mark_all_post_as_read()

    def watch_active_view(self, old_view: ActiveView, new_view: ActiveView) -> None:
        if old_view == new_view:
            return

        if new_view == ActiveView.IDLE:
            self.tabloid.border_title = "lazyfeed"
            return

        if new_view == ActiveView.ALL:
            self.tabloid.border_title = "lazyfeed/all"
            self._load_posts()
            return

        if new_view == ActiveView.PENDING:
            self.tabloid.border_title = "lazyfeed"
            self._load_posts(read=False)
            return

        if new_view == ActiveView.SAVED:
            self.tabloid.border_title = "lazyfeed/saved"
            self._load_posts(saved_for_later=True)
            return

        if new_view == ActiveView.FAV:
            self.tabloid.border_title = "lazyfeed/fav"
            self._load_posts(favorite=True)

    def _gen_row_content(self, post: Post) -> tuple[str, str, str]:
        """
        Generate the content for a row for the given post.
        """

        saved = "\uf02e" if post.saved_for_later else ""
        fav = "\uf005" if post.favorite else ""
        label = f"[bold][{post.feed.title}][/bold] {post.title}"
        if post.read:
            label = f"[strike]{label}[/]"

        return saved, fav, label

    def _pop_post(self, row_id: str) -> bool:
        if self.active_view == ActiveView.PENDING and not self._settings.app.show_read:
            self.tabloid.remove_row(row_id)
            return True

        return False

    def _load_posts(self, **kwargs) -> None:
        self.tabloid.clear()

        sort_by = self._settings.app.sort_by
        sort_order = self._settings.app.sort_order
        sort_order_ascending = sort_order == "ascending" or sort_order == "asc"

        posts = self.post_repository.get_sorted(
            sort_by=sort_by,
            ascending=sort_order_ascending,
            **kwargs,
        )

        for post in posts:
            self.tabloid.add_row(*self._gen_row_content(post), key=f"{post.id}")

    def _mark_all_post_as_read(self) -> None:
        self.tabloid.loading = True

        try:
            self.post_repository.mark_all_as_read()
            self.active_view = ActiveView.IDLE

            self.tabloid.clear()

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

        timeout = aiohttp.ClientTimeout(
            total=self._settings.client.timeout,
            connect=self._settings.client.connect_timeout,
        )
        headers = self._settings.client.headers
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as client:
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
                    entry_published_parsed = entry.get("published_parsed", None)
                    if not entry_link or not entry_title:
                        self.notify(
                            f"Something bad happened while fetching '{entry.title}'",
                            severity="error",
                        )
                        continue

                    published_at = None
                    if entry_published_parsed:
                        published_at = datetime(
                            *entry_published_parsed[:6],
                            tzinfo=timezone.utc,
                        )

                    new_entries.append(
                        Post(
                            feed=feed,
                            url=entry_link,
                            title=entry_title,
                            summary=entry_summary,
                            published_at=published_at,
                        )
                    )

                self.post_repository.add_in_batch(new_entries)

        self.active_view = ActiveView.PENDING
        self.tabloid.loading = False
        self.tabloid.focus()


if __name__ == "__main__":
    import os
    from lazyfeed.models import Feed

    os.environ["APP__DB_URL"] = "sqlite:///:memory:"

    settings = Settings()
    engine = create_engine(settings.app.db_url)
    init_db(engine)

    with Session(engine) as session:
        feed_repo = FeedRepository(session)
        feed_repo.add(
            Feed(
                title="Lorem RSS",
                url="https://lorem-rss.herokuapp.com/feed",
            )
        )

        app = LazyFeedApp(session, settings)
        app.run()
