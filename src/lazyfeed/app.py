import asyncio
import sys
import aiohttp
from sqlalchemy import create_engine, not_
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer
from textual.worker import Worker, WorkerState
from lazyfeed.db import init_db
from lazyfeed.feeds import fetch_feed, fetch_feed_entries
from lazyfeed.messages import DeleteFeed, EditFeed, MarkAllAsRead, MarkAsRead, NewFeed
from lazyfeed.models import Feed, Item
from lazyfeed.settings import APP_NAME, Settings
from lazyfeed.utils import import_opml, console
from lazyfeed.widgets import CustomHeader, ItemTable, RSSFeedTree


class LazyFeedApp(App):
    """
    A simple RSS feed reader for the terminal.
    """

    # TODO: add option to check if fetch feeds or not at start.
    # TODO: check 'auto_read' on quit.
    # TODO: add help modal.
    # TODO: add option to sorting items and feeds.

    TITLE = APP_NAME
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = "global.tcss"

    BINDINGS = [
        Binding("?", "display_help", "help"),
        Binding("ctrl+c,escape,q", "quit", "quit"),
        # Binding("ctrl+a", "mark_all_as_read", "mark all as read"),
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
        self.session.close()
        self.exit(return_code=0)

    async def action_reload_all(self) -> None:
        self.fetch_items()

    async def on_mount(self) -> None:
        self.rss_feed_tree = self.query_one(RSSFeedTree)
        self.item_table = self.query_one(ItemTable)

        self.update_feed_tree()
        self.update_item_table()

    @on(NewFeed)
    async def add_new_feed(self, message: NewFeed) -> None:
        try:
            # TODO: add client setttings
            async with aiohttp.ClientSession() as client_session:
                url = message.url
                title = message.title

                feed_in_db = self.session.query(Feed).where(Feed.url == url).first()
                if feed_in_db:
                    self.notify("feed already exists")
                    return

                feed = await fetch_feed(client_session, url, title)
                self.session.add(feed)
                self.session.commit()

                self.notify("new feed added")

                self.update_feed_tree()
                self.fetch_items()

        except RuntimeError as e:
            self.session.rollback()
            self.notify(f"{e}")

    @on(EditFeed)
    async def update_feed(self, message: EditFeed) -> None:
        try:
            feed_in_db = self.session.query(Feed).where(Feed.url == message.url).first()
            if not feed_in_db:
                self.notify("feed doesn't exists in the database")
                return

            if message.title:
                feed_in_db.title = message.title

            feed_in_db.url = message.url
            self.session.commit()

            self.notify("feed updated")

            self.update_feed_tree()
            self.fetch_items()
        except IntegrityError:
            self.session.rollback()
            self.notify("something went wrong while updating feed")
        except SQLAlchemyError:
            self.session.rollback()
            self.notify("something went wrong while updating feed")

    @on(DeleteFeed)
    async def delete_feed(self, message: DeleteFeed) -> None:
        try:
            feed_in_db = self.session.query(Feed).where(Feed.url == message.url).one()
            self.session.delete(feed_in_db)
            self.session.commit()

            self.notify("feed deleted")

            self.update_feed_tree()
            self.fetch_items()
        except NoResultFound:
            self.notify("feed doesn't exists in the database")
        except SQLAlchemyError:
            self.session.rollback()
            self.notify("something went wrong while deleting feed")

    @on(MarkAsRead)
    async def mark_item_as_read(self, message: MarkAsRead) -> None:
        item_id = message.item_id
        try:
            self.session.query(Item).where(Item.id == item_id).update({"is_read": True})
            self.session.commit()

            self.item_table.remove_row(row_key=f"{item_id}")
        except Exception as e:
            self.session.rollback()
            self.notify(f"something went wrong while updating item: {e}")

    @on(MarkAllAsRead)
    async def mark_all_items_as_read(self) -> None:
        try:
            self.session.query(Item).update({"is_read": True})
            self.session.commit()
            self.notify("all items marked as 'read'")

            self.update_item_table()
        except Exception as e:
            self.session.rollback()
            self.notify(f"something went wrong while updating items: {e}")

    def update_feed_tree(self) -> None:
        self.rss_feed_tree.loading = True

        try:
            feeds = self.session.query(Feed).order_by(Feed.title).all()
            self.rss_feed_tree.mount_feeds(feeds)
        except Exception as e:
            self.notify(f"something went wrong while getting feeds: {e}")
        finally:
            self.rss_feed_tree.loading = False

    def update_item_table(self) -> None:
        self.item_table.loading = True

        try:
            items = (
                self.session.query(Item)
                .where(not_(Item.is_read))
                .order_by(Item.published_at.desc())
                .all()
            )
            self.item_table.mount_items(items)
        except Exception as e:
            self.notify(f"something went wrong while getting items: {e}")
        finally:
            self.item_table.loading = False

    @work(exclusive=True)
    async def fetch_items(self) -> None:
        try:
            # TODO: add client setttings
            async with aiohttp.ClientSession() as client_session:
                feeds = self.session.query(Feed).all()
                for feed in feeds:
                    new_entries = []
                    entries, etag = await fetch_feed_entries(
                        client_session,
                        feed.url,
                        feed.etag,
                    )

                    if not entries:
                        continue

                    feed.etag = etag
                    self.session.commit()

                    for entry in entries:
                        item_in_db = (
                            self.session.query(Item)
                            .where(Item.url == entry.link)
                            .first()
                        )
                        if item_in_db:
                            continue

                        new_entries.append(entry)

                    for entry in new_entries:
                        # TODO: check other attributes
                        title = entry.get("title", entry.link)
                        url = entry.link

                        item = Item(title=title, url=url, feed=feed)
                        self.session.add(item)

                self.session.commit()
        except RuntimeError as e:
            self.notify(f"something went wrong: {e}")
        except Exception as e:
            self.notify(f"something went wrong: {e}")

    @on(Worker.StateChanged)
    def on_fetch_items_state(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.PENDING or event.state == WorkerState.RUNNING:
            self.item_table.loading = True
        else:
            self.update_item_table()


def main():
    async def _fetch_new_feeds(session: Session, new_feeds: list[str]) -> None:
        try:
            # TODO: add client setttings
            async with aiohttp.ClientSession() as client_session:
                for feed_url in new_feeds:
                    console.print(f'🕓 fetching "{feed_url}"')
                    feed = await fetch_feed(client_session, feed_url)

                    console.print(f'✅ fetched correctly "{feed_url}"')
                    session.add(feed)
                    session.commit()
        except RuntimeError as e:
            session.rollback()
            console.print(f"❌ something went wrong while fetching feeds: {e}")

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

            feeds_in_db = [feed.url for feed in session.query(Feed).all()]
            new_feeds = [feed for feed in feeds_in_file if feed not in feeds_in_db]
            if new_feeds:
                console.print(f"✅ found {len(new_feeds)} new feeds")

                status.update("[green]fetching new feeds...[/]")
                asyncio.run(_fetch_new_feeds(session, new_feeds))
            else:
                console.print("✅ all feeds had been already added")

            return

    app.run()


if __name__ == "__main__":
    main()
