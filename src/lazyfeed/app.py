import aiohttp
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Static
from lazyfeed.db import init_db
from lazyfeed.feeds.fetch import fetch_feed
from lazyfeed.help_modal import HelpModal
from lazyfeed.messages import DeleteFeed, EditFeed, NewFeed
from lazyfeed.models import Feed
from lazyfeed.settings import APP_NAME, Settings
from lazyfeed.widgets.rss_feed_tree import RSSFeedTree


class LazyFeedApp(App):
    """
    A simple RSS feed reader for the terminal.
    """

    # TODO: add option to check if fetch feeds or not at start.
    # TODO: check 'auto_read' on quit.

    TITLE = APP_NAME
    CSS_PATH = "global.tcss"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("?", "display_help", "help"),
        Binding("ctrl+c,escape,q", "quit", "quit"),
        # Binding("r", "refresh", "Reload", show=False),
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
        yield Footer()

    def action_display_help(self) -> None:
        self.push_screen(HelpModal())

    def on_mount(self) -> None:
        self.rss_feed_tree = self.query_one(RSSFeedTree)

        self.load_feeds()

    @on(NewFeed)
    async def save_new_feed(self, message: NewFeed) -> None:
        session = self.Session()
        try:
            async with aiohttp.ClientSession() as client_session:
                feed_in_db = session.query(Feed).where(Feed.url == message.url).first()
                if feed_in_db:
                    self.notify("feed already exists in the database")
                    return

                feed = await fetch_feed(client_session, message.url, message.title)
                session.add(feed)
                session.commit()

                self.load_feeds()
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

            self.load_feeds()
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
            if not feed_in_db:
                self.notify("feed doesn't exists in the database")
                return

            session.delete(feed_in_db)
            session.commit()

            self.load_feeds()
        except NoResultFound:
            self.notify("feed doesn't exists in the database")
        except SQLAlchemyError:
            session.rollback()
            self.notify("something went wrong while deleting feed")
        finally:
            session.close()

    def load_feeds(self) -> None:
        session = self.Session()
        try:
            feeds = session.query(Feed).all()
            self.rss_feed_tree.mount_feeds(feeds)
        except Exception as e:
            self.notify(f"something went wrong while getting feeds: {e}")
        finally:
            session.close()


def main():
    settings = Settings()
    app = LazyFeedApp(settings)
    app.run()


if __name__ == "__main__":
    main()
