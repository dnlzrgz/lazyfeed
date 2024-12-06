import aiohttp
from sqlalchemy import create_engine, not_
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Static
from lazyfeed.db import init_db
from lazyfeed.feeds import fetch_feed, fetch_feed_entries
from lazyfeed.help_modal import HelpModal
from lazyfeed.messages import DeleteFeed, EditFeed, NewFeed
from lazyfeed.models import Feed, Item
from lazyfeed.settings import APP_NAME, Settings
from lazyfeed.widgets.items_table import ItemsTable
from lazyfeed.widgets.rss_feed_tree import RSSFeedTree


class LazyFeedApp(App):
    """
    A simple RSS feed reader for the terminal.
    """

    # TODO: add option to check if fetch feeds or not at start.
    # TODO: check 'auto_read' on quit.
    # TODO: add binding to mark all as read.

    TITLE = APP_NAME
    CSS_PATH = "global.tcss"
    ENABLE_COMMAND_PALETTE = False

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

        self.Session = sessionmaker(bind=engine)

    def compose(self) -> ComposeResult:
        yield Static("lazyfeed")
        yield RSSFeedTree(label="*")
        yield ItemsTable()
        yield Footer()

    def action_display_help(self) -> None:
        self.push_screen(HelpModal())

    async def on_mount(self) -> None:
        self.rss_feed_tree = self.query_one(RSSFeedTree)
        self.items_table = self.query_one(ItemsTable)

        self.refresh_feed_tree()
        self.refresh_items_table()

        self.fetch_entries()

    @on(NewFeed)
    async def save_new_feed(self, message: NewFeed) -> None:
        session = self.Session()
        try:
            # TODO: add client setttings
            async with aiohttp.ClientSession() as client_session:
                feed_in_db = session.query(Feed).where(Feed.url == message.url).first()
                if feed_in_db:
                    self.notify("feed already exists in the database")
                    return

                feed = await fetch_feed(client_session, message.url, message.title)
                session.add(feed)
                session.commit()

                self.refresh_feed_tree()
                self.notify("new feed added")
        except RuntimeError as e:
            session.rollback()
            self.notify(f"{e}")
        finally:
            session.close()

    @on(EditFeed)
    async def update_feed(self, message: EditFeed) -> None:
        session = self.Session()
        try:
            feed_in_db = session.query(Feed).where(Feed.url == message.url).first()
            if not feed_in_db:
                self.notify("feed doesn't exists in the database")
                return

            if message.title:
                feed_in_db.title = message.title

            feed_in_db.url = message.url
            session.commit()

            self.refresh_feed_tree()
            self.notify("feed updated")
        except IntegrityError:
            session.rollback()
            self.notify("feed already exists in the database")
        except SQLAlchemyError:
            session.rollback()
            self.notify("something went wrong while updating feed")
        finally:
            session.close()

    @on(DeleteFeed)
    async def delete_feed(self, message: DeleteFeed):
        session = self.Session()
        try:
            feed_in_db = session.query(Feed).where(Feed.url == message.url).one()
            session.delete(feed_in_db)
            session.commit()

            self.refresh_feed_tree()
        except NoResultFound:
            self.notify("feed doesn't exists in the database")
        except SQLAlchemyError:
            session.rollback()
            self.notify("something went wrong while deleting feed")
        finally:
            session.close()

    def refresh_items_table(self) -> None:
        session = self.Session()
        try:
            items = session.query(Item).where(not_(Item.is_read)).all()
            self.items_table.mount_items(items)
        except Exception as e:
            self.notify(f"something went wrong while getting feeds: {e}")
        finally:
            session.close()

    def refresh_feed_tree(self) -> None:
        session = self.Session()
        try:
            feeds = session.query(Feed).all()
            self.rss_feed_tree.mount_feeds(feeds)
        except Exception as e:
            self.notify(f"something went wrong while getting feeds: {e}")
        finally:
            session.close()

    @work(exclusive=True)
    async def fetch_entries(self) -> None:
        session = self.Session()
        try:
            feeds = session.query(Feed).all()
        except Exception as e:
            self.notify(f"something went wrong while getting feeds: {e}")
            session.close()
            return

        try:
            # TODO: add client setttings
            async with aiohttp.ClientSession() as client_session:
                for feed in feeds:
                    new_entries = []
                    entries = await fetch_feed_entries(client_session, feed.url)
                    for entry in entries:
                        item_in_db = (
                            session.query(Item).where(Item.url == entry.link).first()
                        )
                        if item_in_db:
                            continue

                        new_entries.append(entry)

                    for entry in new_entries:
                        # TODO: check other attributes
                        title = entry.get("title", entry.link)
                        url = entry.link

                        item = Item(title=title, url=url, feed=feed)
                        session.add(item)

                session.commit()
        except RuntimeError as e:
            self.notify(f"something went wrong: {e}")
        except Exception as e:
            self.notify(f"something went wrong: {e}")
        finally:
            session.close()


def main():
    settings = Settings()
    app = LazyFeedApp(settings)
    app.run()


if __name__ == "__main__":
    main()
