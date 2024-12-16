import asyncio
from contextlib import asynccontextmanager
import sys
import aiohttp
from sqlalchemy import create_engine, delete, exists, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer
from textual.worker import Worker, WorkerState
from lazyfeed.db import init_db
from lazyfeed.feeds import fetch_feed, fetch_feed_entries
from lazyfeed.models import Feed, Item
from lazyfeed.settings import APP_NAME, Settings
from lazyfeed.utils import import_opml, console
from lazyfeed.widgets import CustomHeader, ItemTable, RSSFeedTree
from lazyfeed.widgets.modals import AddFeedModal, EditFeedModal, ConfirmActionModal
import lazyfeed.messages as messages


@asynccontextmanager
async def http_client_session(timeout: int, connect_timeout: int, headers: dict):
    client_timeout = aiohttp.ClientTimeout(
        total=timeout,
        connect=connect_timeout,
    )

    async with aiohttp.ClientSession(
        timeout=client_timeout, headers=headers
    ) as session:
        yield session


class LazyFeedApp(App):
    """
    A simple RSS feed reader for the terminal.
    """

    # TODO: add option to check if fetch feeds or not at start.
    # TODO: add help modal.
    # TODO: add option to sorting items and feeds.

    TITLE = APP_NAME
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = "global.tcss"

    BINDINGS = [
        Binding("?", "display_help", "help"),
        Binding("ctrl+c,escape,q", "quit", "quit"),
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
            app_name=APP_NAME,
            version=self.settings.version,
        )
        yield RSSFeedTree(label="*")
        yield ItemTable()
        yield Footer()

    def action_display_help(self) -> None:
        self.notify("Show help")

    async def action_quit(self) -> None:
        if self.settings.auto_read:
            try:
                stmt = update(Item).where(Item.is_read.is_(False)).values(is_read=True)
                self.session.execute(stmt)
                self.session.commit()
            except Exception:
                self.session.rollback()

        self.session.close()
        self.exit(return_code=0)

    async def action_reload_all(self) -> None:
        self.fetch_items()

    async def on_mount(self) -> None:
        self.rss_feed_tree = self.query_one(RSSFeedTree)
        self.item_table = self.query_one(ItemTable)

        self.update_feed_tree()
        if self.settings.auto_load:
            self.fetch_items()
        else:
            self.update_item_table()

    @on(messages.AddFeed)
    async def add_feed(self) -> None:
        async def callback(response: dict | None = None) -> None:
            if not response:
                return

            title = response.get("title", "")
            url = response.get("url")
            assert url

            try:
                async with http_client_session(
                    self.settings.http_client.timeout,
                    self.settings.http_client.connect_timeout,
                    self.settings.http_client.headers,
                ) as client_session:
                    stmt = select(exists().where(Feed.url == url))
                    feed_in_db = self.session.execute(stmt).scalar()
                    if feed_in_db:
                        self.notify("feed already exists", severity="error")
                        return

                    feed = await fetch_feed(client_session, url, title)
                    self.session.add(feed)
                    self.session.commit()

                    self.notify("new feed added")

                    self.update_feed_tree()
                    self.fetch_items()
            except (RuntimeError, Exception) as e:
                self.session.rollback()
                self.notify(
                    f"something went wrong while saving new feed: {e}", severity="error"
                )

        self.push_screen(AddFeedModal(), callback)

    @on(messages.EditFeed)
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
            try:
                if title:
                    # TODO: handle no-title case
                    feed_in_db.title = title

                feed_in_db.url = url
                self.session.commit()

                self.notify("feed updated")

                self.update_feed_tree()
                self.fetch_items()
            except IntegrityError:
                self.session.rollback()
                self.notify(
                    "something went wrong while updating feed", severity="error"
                )
            except SQLAlchemyError:
                self.session.rollback()
                self.notify(
                    "something went wrong while updating feed", severity="error"
                )

        self.push_screen(EditFeedModal(feed_in_db.url, feed_in_db.title), callback)

    @on(messages.DeleteFeed)
    async def delete_feed(self, message: messages.DeleteFeed) -> None:
        stmt = select(Feed).where(Feed.id == message.id)
        feed_in_db = self.session.execute(stmt).scalar()
        if not feed_in_db:
            self.notify("feed not found", severity="error")
            return

        async def callback(response: bool | None = False) -> None:
            if not response:
                return

            try:
                stmt = delete(Feed).where(Feed.id == feed_in_db.id)
                self.session.execute(stmt)
                self.session.commit()

                self.notify(f'feed "{feed_in_db.title}" deleted')
                self.update_feed_tree()
                self.fetch_items()
            except SQLAlchemyError:
                self.session.rollback()
                self.notify(
                    "something went wrong while deleting feed", severity="error"
                )

        self.push_screen(
            ConfirmActionModal(
                border_title="delete feed",
                message=f'are you sure you want to delete "{feed_in_db.title}"?',
                action_name="delete",
            ),
            callback,
        )

    @on(messages.MarkAsRead)
    async def mark_item_as_read(self, message: messages.MarkAsRead) -> None:
        item_id = message.item_id
        try:
            stmt = update(Item).where(Item.id == item_id).values(is_read=True)
            result = self.session.execute(stmt)
            self.session.commit()

            if result.rowcount > 0:
                self.item_table.remove_row(row_key=f"{item_id}")
        except Exception as e:
            self.session.rollback()
            self.notify(
                f"something went wrong while updating item: {e}", severity="error"
            )

    @on(messages.MarkAllAsRead)
    async def mark_all_items_as_read(self) -> None:
        async def callback(response: bool | None = False) -> None:
            if not response:
                return

            try:
                stmt = update(Item).where(Item.is_read.is_(False)).values(is_read=True)
                self.session.execute(stmt)
                self.session.commit()
                self.notify("all items marked as read")

                self.update_item_table()
            except Exception as e:
                self.session.rollback()
                self.notify(
                    f"something went wrong while updating items: {e}", severity="error"
                )

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
    async def show_all_items(self) -> None:
        self.update_item_table()

    @on(messages.OpenInBrowser)
    async def open_in_browser(self, message: messages.OpenInBrowser) -> None:
        item_id = message.item_id

        try:
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

                self.item_table.remove_row(row_key=f"{item_id}")
            else:
                self.notify("item not found", severity="error")
        except Exception as e:
            self.session.rollback()
            self.notify(
                f"something went wrong while updating items: {e}", severity="error"
            )

    @on(messages.SaveForLater)
    async def save_for_later(self, message: messages.SaveForLater) -> None:
        item_id = message.item_id

        try:
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
            else:
                self.notify("item not found", severity="error")
        except Exception as e:
            self.session.rollback()
            self.notify(
                f"something went wrong while updating items: {e}", severity="error"
            )

    @on(messages.ShowSavedForLater)
    async def load_saved_for_later(self) -> None:
        self.item_table.loading = True

        try:
            stmt = (
                select(Item)
                .where(Item.is_saved.is_(True))
                .order_by(Item.published_at.desc())
            )
            results = self.session.execute(stmt).scalars().all()
            self.item_table.mount_items(results)
        except Exception as e:
            self.notify(f"something went wrong while getting items: {e}")
        finally:
            self.item_table.loading = False

    def update_feed_tree(self) -> None:
        self.rss_feed_tree.loading = True

        try:
            stmt = select(Feed.id, Feed.title).order_by(Feed.title.asc())
            results = self.session.execute(stmt).all()
            self.rss_feed_tree.mount_feeds(results)
        except Exception as e:
            self.notify(f"something went wrong while getting feeds: {e}")
        finally:
            self.rss_feed_tree.loading = False

    def update_item_table(self) -> None:
        self.item_table.loading = True

        try:
            stmt = (
                select(Item)
                .where(Item.is_read.is_(False))
                .order_by(Item.published_at.desc())
            )
            results = self.session.execute(stmt).scalars().all()
            self.item_table.mount_items(results)
        except Exception as e:
            self.notify(f"something went wrong while getting items: {e}")
        finally:
            self.item_table.loading = False

    async def process_feed(
        self, client_session: aiohttp.ClientSession, feed: Feed
    ) -> tuple[list[dict], Feed]:
        entries, etag = await fetch_feed_entries(client_session, feed.url, feed.etag)
        if not entries:
            return [], feed

        feed.etag = etag

        new_entries = []
        for entry in entries:
            stmt = select(Item).where(Item.url == entry.link)
            result = self.session.execute(stmt).scalar()
            if result:
                continue

            new_entries.append(entry)

        return new_entries, feed

    @work(exclusive=True)
    async def fetch_items(self) -> None:
        try:
            async with http_client_session(
                self.settings.http_client.timeout,
                self.settings.http_client.connect_timeout,
                self.settings.http_client.headers,
            ) as client_session:
                feeds = self.session.query(Feed).all()
                tasks = []

                for feed in feeds:
                    tasks.append(self.process_feed(client_session, feed))

                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        self.notify(
                            f"something went wrong while fetching entries: {result}"
                        )
                        continue

                    new_entries = []
                    entries, feed = result
                    for entry in entries:
                        new_entries.append(
                            Item(
                                title=entry.get("title", ""),
                                author=entry.get("author", ""),
                                url=entry.link,
                                feed=feed,
                            )
                        )

                    self.session.add_all(new_entries)
                    self.session.commit()

        except RuntimeError as e:
            self.session.rollback()
            self.notify(f"something went wrong: {e}")
        except Exception as e:
            self.session.rollback()
            self.notify(f"something went wrong: {e}")

    @on(Worker.StateChanged)
    def on_fetch_items_state(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.PENDING or event.state == WorkerState.RUNNING:
            self.item_table.loading = True
        else:
            self.update_item_table()


async def fetch_new_feeds(
    settings: Settings, session: Session, feeds: list[str]
) -> None:
    async with http_client_session(
        settings.http_client.timeout,
        settings.http_client.connect_timeout,
        settings.http_client.headers,
    ) as client_session:
        tasks = [fetch_feed(client_session, feed) for feed in feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                console.print(f"❌ something went wrong fetching feed: {result}")
                continue

            try:
                session.add(result)
                session.commit()
                console.print(f'✅ added "{result.url}"')
            except Exception as e:
                session.rollback()
                console.print(
                    f"❌ something went wrong while saving feeds to the database: {e}"
                )


def main():
    settings = Settings()
    app = LazyFeedApp(settings)
    session = app.session

    if not sys.stdin.isatty():
        with console.status(
            "[green]importing feeds from file... please, wait a moment",
            spinner="earth",
        ) as status:
            opml_content = sys.stdin.read()
            feeds_in_file = import_opml(opml_content)

            console.print("✅ file read correctly")

            stmt = select(Feed.url)
            results = session.execute(stmt).scalars().all()
            new_feeds = [feed for feed in feeds_in_file if feed not in results]
            if not new_feeds:
                console.print("✅ all feeds had been already added")
                return

            status.update(f"[green]fetching {len(new_feeds)} new feeds...[/]")
            asyncio.run(fetch_new_feeds(settings, session, new_feeds))
            return

    app.run()


if __name__ == "__main__":
    main()
