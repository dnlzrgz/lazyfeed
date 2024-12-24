import asyncio
from datetime import date
from sqlalchemy import create_engine, delete, exists, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import var
from textual.widget import Widget
from textual.widgets import Footer
from textual.worker import Worker, WorkerState
from lazyfeed.db import init_db
from lazyfeed.decorators import fetch_guard, rollback_session
from lazyfeed.feeds import fetch_content, fetch_entries, fetch_feed
from lazyfeed.http_client import http_client_session
from lazyfeed.models import Feed, Item
from lazyfeed.settings import APP_NAME, DB_URL, Settings
from lazyfeed.widgets import (
    CustomHeader,
    ItemTable,
    RSSFeedTree,
    ItemScreen,
)
from lazyfeed.widgets.modals import (
    AddFeedModal,
    EditFeedModal,
    ConfirmActionModal,
    HelpModal,
)
import lazyfeed.messages as messages


class LazyFeedApp(App):
    """
    A simple and modern RSS feed reader for the terminal.
    """

    TITLE = APP_NAME
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = "global.tcss"

    BINDINGS = [
        Binding("ctrl+c,escape,q", "quit", "quit"),
        Binding("?,f1", "help", "help"),
        Binding("R", "refresh", "refresh"),
    ]

    is_fetching: var[bool] = var(False)
    show_read: var[bool] = var(False)

    def __init__(self, settings: Settings):
        super().__init__()

        self.settings = settings
        self.theme = self.settings.theme

        sort_column = getattr(Item, self.settings.sort_by, Item.published_at)
        self.sort_order = sort_column.desc()
        if self.settings.sort_order == "ascending":
            self.sort_order = sort_column.asc()

        engine = create_engine(f"sqlite:///{DB_URL}")
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

    async def on_mount(self) -> None:
        self.item_table = self.query_one(ItemTable)
        self.rss_feed_tree = self.query_one(RSSFeedTree)

        self.item_table.focus()

        await self.sync_feeds()
        await self.sync_items()

        if self.settings.auto_load:
            self.fetch_items()

    def action_help(self) -> None:
        widget = self.focused
        if not widget:
            self.notify("first you have to focus a widget", severity="warning")
            return

        self.push_screen(HelpModal(widget=widget))

    @fetch_guard
    @rollback_session()
    async def action_quit(self) -> None:
        if self.settings.auto_read:
            stmt = update(Item).where(Item.is_read.is_(False)).values(is_read=True)
            self.session.execute(stmt)
            self.session.commit()

        self.session.close()
        self.exit(return_code=0)

    @fetch_guard
    async def action_refresh(self) -> None:
        self.fetch_items()

    def toggle_widget_loading(self, widget: Widget, loading: bool = False) -> None:
        widget.loading = loading

    @on(messages.AddFeed)
    @fetch_guard
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
                await self.sync_feeds()

        self.push_screen(AddFeedModal(), callback)

    @on(messages.EditFeed)
    @fetch_guard
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

            await self.sync_feeds()

        self.push_screen(EditFeedModal(feed_in_db.url, feed_in_db.title), callback)

    @on(messages.DeleteFeed)
    @fetch_guard
    @rollback_session("something went wrong while removing feed")
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

            self.notify(f'feed "{feed_in_db.title}" removed')

            await self.sync_feeds()
            await self.sync_items()

        self.push_screen(
            ConfirmActionModal(
                border_title="remove feed",
                message=f'are you sure you want to remove "{feed_in_db.title}"?',
                action_name="remove",
            ),
            callback,
        )

    @on(messages.FilterByFeed)
    @fetch_guard
    @rollback_session("something went wrong while getting items from feed")
    async def filter_by_feed(self, message: messages.FilterByFeed) -> None:
        self.show_read = True

        stmt = (
            select(Item).where(Item.feed_id.is_(message.id)).order_by(self.sort_order)
        )
        results = self.session.execute(stmt).scalars().all()

        self.item_table.mount_items(results)
        self.item_table.focus()

    @on(messages.MarkAsRead)
    @rollback_session("something went wrong while updating item")
    async def mark_item_as_read(self, message: messages.MarkAsRead) -> None:
        item_id = message.item_id

        stmt = select(Item).where(Item.id == item_id)
        result = self.session.execute(stmt).scalar()
        if not result:
            self.notify("something went wrong while getting the item", severity="error")
            return

        stmt = update(Item).where(Item.id == item_id).values(is_read=not result.is_read)
        self.session.execute(stmt)
        self.session.commit()

        self.session.refresh(result)

        if self.show_read:
            self.item_table.update_item(f"{item_id}", result)
        else:
            self.item_table.remove_row(row_key=f"{item_id}")

        self.item_table.border_subtitle = f"{self.item_table.row_count}"

        stmt = select(Feed).where(Feed.id == result.feed_id)
        result = self.session.execute(stmt).scalar()
        if result:
            stmt = select(
                func.coalesce(func.count(Item.id).filter(Item.is_read.is_(False)), 0)
            ).where(Item.feed_id == result.id)
            pending_posts = self.session.execute(stmt).scalar()

            self.rss_feed_tree.update_feed((result.id, pending_posts, result.title))

    @on(messages.MarkAllAsRead)
    @fetch_guard
    @rollback_session("something went wrong while updating items")
    async def mark_all_items_as_read(self) -> None:
        async def callback(response: bool | None = False) -> None:
            if not response:
                return

            stmt = update(Item).where(Item.is_read.is_(False)).values(is_read=True)
            self.session.execute(stmt)
            self.session.commit()
            self.notify("all items marked as read")

            await self.sync_feeds()
            await self.sync_items()

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
    @fetch_guard
    @rollback_session(
        error_message="something went wrong while getting items",
        callback=lambda self: self.toggle_widget_loading(self.item_table),
    )
    async def show_all_items(self) -> None:
        self.show_read = True

        stmt = select(Item).order_by(self.sort_order)
        results = self.session.execute(stmt).scalars().all()
        self.item_table.mount_items(results)

    @on(messages.ShowPending)
    @fetch_guard
    async def show_pending_items(self) -> None:
        self.show_read = False
        await self.sync_items()

    @on(messages.Open)
    @fetch_guard
    @rollback_session("something went wrong while updating item")
    async def open_item(self, message: messages.Open) -> None:
        item_id = message.item_id

        stmt = select(Item).where(Item.id == item_id)
        result = self.session.execute(stmt).scalar()
        if result:
            self.push_screen(ItemScreen(result))
            self.post_message(messages.MarkAsRead(item_id))

    @on(messages.OpenInBrowser)
    @fetch_guard
    @rollback_session("something went wrong while updating item")
    async def open_in_browser(self, message: messages.OpenInBrowser) -> None:
        item_id = message.item_id

        stmt = select(Item).where(Item.id == item_id)
        result = self.session.execute(stmt).scalar()
        if result:
            self.open_url(result.url)
            self.post_message(messages.MarkAsRead(item_id))
        else:
            self.notify("item not found", severity="error")

    @on(messages.SaveForLater)
    @fetch_guard
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
    @fetch_guard
    @rollback_session(
        error_message="something went wrong while getting items",
        callback=lambda self: self.toggle_widget_loading(self.item_table),
    )
    async def load_saved_for_later(self) -> None:
        self.show_read = True

        stmt = select(Item).where(Item.is_saved.is_(True)).order_by(self.sort_order)
        results = self.session.execute(stmt).scalars().all()
        self.item_table.mount_items(results)

    @on(messages.ShowToday)
    @fetch_guard
    @rollback_session(
        error_message="something went wrong while getting items",
        callback=lambda self: self.toggle_widget_loading(self.item_table),
    )
    async def load_today_items(self) -> None:
        self.show_read = True

        today = date.today()

        stmt = (
            select(Item)
            .where(func.date(Item.published_at) == today)
            .order_by(self.sort_order)
        )
        results = self.session.execute(stmt).scalars().all()
        self.item_table.mount_items(results)

    @rollback_session(
        error_message="something went wrong while getting feeds",
        callback=lambda self: self.toggle_widget_loading(self.rss_feed_tree),
    )
    async def sync_feeds(self) -> None:
        stmt = (
            select(
                Feed.id,
                func.coalesce(
                    func.count(Item.id).filter(Item.is_read.is_(False)), 0
                ).label("pending_posts"),
                Feed.title,
            )
            .outerjoin(Item)
            .group_by(Feed.id, Feed.title)
            .order_by(Feed.title.asc())
        )
        results = self.session.execute(stmt).all()
        self.rss_feed_tree.mount_feeds(results)

    @rollback_session(
        error_message="something went wrong while getting items",
        callback=lambda self: self.toggle_widget_loading(self.item_table),
    )
    async def sync_items(self) -> None:
        stmt = select(Item)
        if not self.show_read:
            stmt = stmt.where(Item.is_read.is_(False))

        stmt = stmt.order_by(self.sort_order)
        results = self.session.execute(stmt).scalars().all()
        self.item_table.mount_items(results)

    @work(exclusive=True)
    async def fetch_items(self) -> None:
        async with http_client_session(self.settings) as client_session:
            feeds = self.session.query(Feed).all()
            n_feeds = len(feeds)

            for i, feed in enumerate(feeds):
                self.item_table.border_title = f"loading... {i + 1}/{n_feeds}"

                tasks = []
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
                except (RuntimeError, Exception) as e:
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
                    self.notify(f"something went wrong while saving items: {e}")

    @on(Worker.StateChanged)
    async def on_fetch_items_state(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.PENDING or event.state == WorkerState.RUNNING:
            self.is_fetching = True
            self.toggle_widget_loading(self.item_table, True)
        else:
            self.is_fetching = False
            self.item_table.border_title = "items"

            await self.sync_items()
            await self.sync_feeds()
