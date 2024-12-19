import asyncio
from sqlalchemy import create_engine, delete, exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer
from textual.worker import Worker, WorkerState
from lazyfeed.db import init_db
from lazyfeed.decorators import rollback_session
from lazyfeed.feeds import fetch_content, fetch_entries, fetch_feed
from lazyfeed.http_client import http_client_session
from lazyfeed.models import Feed, Item
from lazyfeed.settings import APP_NAME, Settings
from lazyfeed.widgets import CustomHeader, ItemTable, RSSFeedTree, ItemScreen
from lazyfeed.widgets.modals import (
    AddFeedModal,
    EditFeedModal,
    ConfirmActionModal,
    HelpModal,
)
import lazyfeed.messages as messages


class LazyFeedApp(App):
    """
    A simple RSS feed reader for the terminal.
    """

    TITLE = APP_NAME
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = "global.tcss"

    BINDINGS = [
        Binding("ctrl+c,escape,q", "quit", "quit"),
        Binding("?,f1", "help", "help"),
        Binding("R", "reload_all", "reload all"),
    ]

    def __init__(self, settings: Settings):
        super().__init__()

        self.settings = settings
        self.theme = self.settings.theme

        engine = create_engine(f"sqlite:///{self.settings.db_url}")
        init_db(engine)

        Session = sessionmaker(bind=engine)
        self.session = Session()

    def compose(self) -> ComposeResult:
        yield CustomHeader(
            title=f"↪ {APP_NAME}",
            subtitle=f"v{self.settings.version}",
        )
        yield RSSFeedTree(label="*")
        yield ItemTable()
        yield Footer()

    def action_help(self) -> None:
        self.push_screen(HelpModal(widget=self.focused))

    @rollback_session()
    async def action_quit(self) -> None:
        if self.settings.auto_read:
            stmt = update(Item).where(Item.is_read.is_(False)).values(is_read=True)
            self.session.execute(stmt)
            self.session.commit()

        self.session.close()
        self.exit(return_code=0)

    async def action_reload_all(self) -> None:
        self.fetch_items()

    async def on_mount(self) -> None:
        self.rss_feed_tree = self.query_one(RSSFeedTree)
        self.item_table = self.query_one(ItemTable)

        self.item_table.focus()

        await self.update_feed_tree()
        if self.settings.auto_load:
            self.fetch_items()
        else:
            await self.update_item_table()

    def toggle_rss_feed_tree_loading(self, loading: bool = False) -> None:
        self.rss_feed_tree.loading = loading

    def toggle_item_table_loading(self, loading: bool = False) -> None:
        self.item_table.loading = loading

    def get_sort_order(self, column_name: str) -> str:
        if self.settings.sort_order == "ascending":
            return column_name.asc()
        else:
            return column_name.desc()

    @on(messages.AddFeed)
    @rollback_session("something went wrong while saving new feed")
    async def add_feed(self) -> None:
        async def callback(response: dict | None = None) -> None:
            if not response:
                return

            title = response.get("title", "")
            url = response.get("url")
            assert url

            async with http_client_session(self.settings) as client_session:
                stmt = select(exists().where(Feed.url == url))
                feed_in_db = self.session.execute(stmt).scalar()
                if feed_in_db:
                    self.notify("feed already exists", severity="error")
                    return

                feed = await fetch_feed(client_session, url, title)
                self.session.add(feed)
                self.session.commit()

                self.notify("new feed added")

                await self.update_feed_tree()
                self.fetch_items()

        self.push_screen(AddFeedModal(), callback)

    @on(messages.EditFeed)
    @rollback_session("something went wrong while updating feed")
    async def update_feed(self, message: messages.EditFeed) -> None:
        stmt = select(Feed).where(Feed.id == message.id)
        feed_in_db = self.session.execute(stmt).scalar()
        if not feed_in_db:
            self.notify("feed not found", severity="error")
            return

        async def callback(response: dict | None = None) -> None:
            if not response:
                return

            title = response.get("title", "")
            url = response.get("url")
            assert url
            if not title:
                async with http_client_session(self.settings) as client_session:
                    feed = await fetch_feed(client_session, url, title)
                    title = feed.title

            feed_in_db.title = title
            feed_in_db.url = url
            self.session.commit()

            self.notify("feed updated")

            await self.update_feed_tree()
            await self.update_item_table()

        self.push_screen(EditFeedModal(feed_in_db.url, feed_in_db.title), callback)

    @on(messages.DeleteFeed)
    @rollback_session("something went wrong while deleting feed")
    async def delete_feed(self, message: messages.DeleteFeed) -> None:
        stmt = select(Feed).where(Feed.id == message.id)
        feed_in_db = self.session.execute(stmt).scalar()
        if not feed_in_db:
            self.notify("feed not found", severity="error")
            return

        async def callback(response: bool | None = False) -> None:
            if not response:
                return

            stmt = delete(Feed).where(Feed.id == feed_in_db.id)
            self.session.execute(stmt)
            self.session.commit()

            self.notify(f'feed "{feed_in_db.title}" deleted')
            await self.update_feed_tree()
            await self.update_item_table()

        self.push_screen(
            ConfirmActionModal(
                border_title="delete feed",
                message=f'are you sure you want to delete "{feed_in_db.title}"?',
                action_name="delete",
            ),
            callback,
        )

    @on(messages.MarkAsRead)
    @rollback_session("something went wrong while updating item")
    async def mark_item_as_read(self, message: messages.MarkAsRead) -> None:
        item_id = message.item_id

        stmt = update(Item).where(Item.id == item_id).values(is_read=True)
        self.session.execute(stmt)
        self.session.commit()

        self.item_table.remove_row(row_key=f"{item_id}")
        self.item_table.border_subtitle = f"{self.item_table.row_count}"

    @on(messages.MarkAllAsRead)
    @rollback_session("something went wrong while updating items")
    async def mark_all_items_as_read(self) -> None:
        async def callback(response: bool | None = False) -> None:
            if not response:
                return

            stmt = update(Item).where(Item.is_read.is_(False)).values(is_read=True)
            self.session.execute(stmt)
            self.session.commit()
            self.notify("all items marked as read")

            await self.update_item_table()

        if self.settings.confirm_before_read:
            self.push_screen(
                ConfirmActionModal(
                    border_title="mark all as read",
                    message="are you sure that you want to mark all items as read?",
                    action_name="confirm",
                ),
                callback,
            )
        else:
            await callback(True)

    @on(messages.ShowAll)
    @rollback_session(
        error_message="something went wrong while getting items",
        callback=lambda self: self.toggle_item_table_loading(),
    )
    async def show_all_items(self) -> None:
        self.toggle_item_table_loading(True)

        sort_column = getattr(Item, self.settings.sort_by, Item.published_at)
        stmt = select(Item).order_by(self.get_sort_order(sort_column))
        results = self.session.execute(stmt).scalars().all()

        self.item_table.mount_items(results)

    @on(messages.ShowPending)
    async def show_pending_items(self) -> None:
        await self.update_item_table()

    @on(messages.Open)
    @rollback_session("something went wrong while marking item as read")
    async def open_item(self, message: messages.Open) -> None:
        item_id = message.item_id

        stmt = select(Item).where(Item.id == item_id)
        result = self.session.execute(stmt).scalar()
        if result:
            self.push_screen(ItemScreen(result))

    @on(messages.OpenInBrowser)
    @rollback_session("something went wrong while marking item as read")
    async def open_in_browser(self, message: messages.OpenInBrowser) -> None:
        item_id = message.item_id

        stmt = select(Item).where(Item.id == item_id)
        result = self.session.execute(stmt).scalar()
        if result:
            self.open_url(result.url)

            stmt = (
                update(Item)
                .where(Item.id == item_id)
                .values(is_read=True, is_saved=False)
            )
            result = self.session.execute(stmt)
            self.session.commit()
            self.post_message(messages.MarkAsRead(item_id))
        else:
            self.notify("item not found", severity="error")

    @on(messages.SaveForLater)
    @rollback_session("something went wrong while updating items")
    async def save_for_later(self, message: messages.SaveForLater) -> None:
        item_id = message.item_id

        stmt = select(Item).where(Item.id == item_id)
        result = self.session.execute(stmt).scalar()
        if result:
            stmt = (
                update(Item)
                .where(Item.id == item_id)
                .values(is_saved=not result.is_saved)
            )
            self.session.execute(stmt)
            self.session.commit()

            self.session.refresh(result)
            self.item_table.update_item(f"{item_id}", result)

    @on(messages.ShowSavedForLater)
    @rollback_session(
        error_message="something went wrong while getting items",
        callback=lambda self: self.toggle_item_table_loading(),
    )
    async def load_saved_for_later(self) -> None:
        self.toggle_item_table_loading(True)

        stmt = (
            select(Item)
            .where(Item.is_saved.is_(True))
            .order_by(Item.published_at.desc())
        )
        results = self.session.execute(stmt).scalars().all()
        self.item_table.mount_items(results)

    @rollback_session(
        error_message="something went wrong while getting feeds",
        callback=lambda self: self.toggle_rss_feed_tree_loading(),
    )
    async def update_feed_tree(self) -> None:
        self.toggle_rss_feed_tree_loading(True)

        stmt = select(Feed.id, Feed.title).order_by(Feed.title.asc())
        results = self.session.execute(stmt).all()
        self.rss_feed_tree.mount_feeds(results)

    @rollback_session(
        error_message="something went wrong while getting items",
        callback=lambda self: self.toggle_item_table_loading(),
    )
    async def update_item_table(self) -> None:
        self.toggle_item_table_loading(True)

        sort_column = getattr(Item, self.settings.sort_by, Item.published_at)
        stmt = (
            select(Item)
            .where(Item.is_read.is_(False))
            .order_by(self.get_sort_order(sort_column))
        )
        results = self.session.execute(stmt).scalars().all()
        self.item_table.mount_items(results)

    @work(exclusive=True)
    async def fetch_items(self) -> None:
        async with http_client_session(self.settings) as client_session:
            feeds = self.session.query(Feed).all()
            tasks = []

            for feed in feeds:
                try:
                    entries, etag = await fetch_entries(
                        client_session, feed.url, feed.etag
                    )
                    if not entries:
                        continue

                    feed.etag = etag
                    for entry in entries:
                        stmt = select(Item).where(Item.url == entry.link)
                        result = self.session.execute(stmt).scalar()
                        if result:
                            continue

                        tasks.append(fetch_content(client_session, entry, feed.id))
                except RuntimeError as e:
                    self.notify(
                        f'something went wrong when parsing feed "{feed.title}": {e}'
                    )

            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful_items = [
                result for result in results if not isinstance(result, Exception)
            ]
            unique_items = {item.url: item for item in successful_items}
            try:
                self.session.add_all(list(unique_items.values()))
                self.session.commit()
            except (IntegrityError, Exception) as e:
                self.session.rollback()
                self.notify(f"something went wrong when saving items: {e}")

    @on(Worker.StateChanged)
    async def on_fetch_items_state(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.PENDING or event.state == WorkerState.RUNNING:
            self.toggle_item_table_loading(True)
        else:
            await self.update_item_table()
