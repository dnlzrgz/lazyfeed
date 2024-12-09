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
from lazyfeed.db import init_db
from lazyfeed.feeds import fetch_feed, fetch_feed_entries
from lazyfeed.messages import DeleteFeed, EditFeed, NewFeed
from lazyfeed.models import Feed, Item
from lazyfeed.settings import APP_NAME, Settings
from lazyfeed.widgets import CustomHeader, ItemsTable, RSSFeedTree
from lazyfeed.utils import import_opml


class LazyFeedApp(App):
    """
    A simple RSS feed reader for the terminal.
    """

    # TODO: add option to check if fetch feeds or not at start.
    # TODO: check 'auto_read' on quit.
    # TODO: add binding to mark all as read.

    TITLE = APP_NAME
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = "global.tcss"

    BINDINGS = [
        Binding("?", "display_help", "help"),
        Binding("ctrl+c,escape,q", "quit", "quit"),
        # Binding("r", "refresh", "refresh"),
        # Binding("R", "reload", "reload"),
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
        yield ItemsTable()
        yield Footer()

    def action_display_help(self) -> None:
        # TODO:
        self.notify("Show help")

    async def action_quit(self) -> None:
        self.session.close()
        self.exit(return_code=0)

    async def on_mount(self) -> None:
        self.rss_feed_tree = self.query_one(RSSFeedTree)
        self.items_table = self.query_one(ItemsTable)

        self.refresh_feed_tree()
        self.refresh_items_table()

        self.fetch_entries()

    @on(NewFeed)
    async def save_new_feed(self, message: NewFeed) -> None:
        try:
            # TODO: add client setttings
            async with aiohttp.ClientSession() as client_session:
                feed_in_db = (
                    self.session.query(Feed).where(Feed.url == message.url).first()
                )
                if feed_in_db:
                    self.notify("feed already exists in the database")
                    return

                feed = await fetch_feed(client_session, message.url, message.title)
                self.session.add(feed)
                self.session.commit()

                self.refresh_feed_tree()
                self.notify("new feed added")
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

            self.refresh_feed_tree()
            self.notify("feed updated")
        except IntegrityError:
            self.session.rollback()
            self.notify("feed already exists in the database")
        except SQLAlchemyError:
            self.session.rollback()
            self.notify("something went wrong while updating feed")

    @on(DeleteFeed)
    async def delete_feed(self, message: DeleteFeed):
        try:
            feed_in_db = self.session.query(Feed).where(Feed.url == message.url).one()
            self.session.delete(feed_in_db)
            self.session.commit()

            self.refresh_feed_tree()
        except NoResultFound:
            self.notify("feed doesn't exists in the database")
        except SQLAlchemyError:
            self.session.rollback()
            self.notify("something went wrong while deleting feed")

    def refresh_items_table(self) -> None:
        try:
            # TODO: sort in order.
            items = self.session.query(Item).where(not_(Item.is_read)).all()
            self.items_table.mount_items(items)
        except Exception as e:
            self.notify(f"something went wrong while getting feeds: {e}")

    def refresh_feed_tree(self) -> None:
        try:
            feeds = self.session.query(Feed).all()
            self.rss_feed_tree.mount_feeds(feeds)
        except Exception as e:
            self.notify(f"something went wrong while getting feeds: {e}")

    @work(exclusive=True)
    async def fetch_entries(self) -> None:
        # TODO: self loading items to true.

        try:
            feeds = self.session.query(Feed).all()
        except Exception as e:
            self.notify(f"something went wrong while getting feeds: {e}")
            return

        try:
            # TODO: add client setttings
            async with aiohttp.ClientSession() as client_session:
                for feed in feeds:
                    new_entries = []
                    entries = await fetch_feed_entries(client_session, feed.url)
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
        finally:
            self.refresh_items_table()


def main():
    async def _fetch_new_feeds(session: Session, new_feeds: list[str]) -> None:
        try:
            # TODO: add client setttings
            async with aiohttp.ClientSession() as client_session:
                for feed_url in new_feeds:
                    feed = await fetch_feed(client_session, feed_url)
                    session.add(feed)
                    session.commit()
        except RuntimeError as _:
            session.rollback()
            # TODO: console out error

    settings = Settings()
    app = LazyFeedApp(settings)
    session = app.session

    if not sys.stdin.isatty():
        # TODO: console out details and progress
        opml_content = sys.stdin.read()
        feeds_in_file = import_opml(opml_content)

        feeds_in_db = [feed.url for feed in session.query(Feed).all()]
        new_feeds = [feed for feed in feeds_in_file if feed not in feeds_in_db]

        asyncio.run(_fetch_new_feeds(session, new_feeds))
        return

    app.run()


if __name__ == "__main__":
    main()
