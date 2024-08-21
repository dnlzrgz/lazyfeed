import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from textual import work
from textual.app import App, ComposeResult
from lazyfeed.db import init_db
from lazyfeed.feeds import fetch_feed, fetch_post
from lazyfeed.help_modal import HelpModal
from lazyfeed.models import Post
from lazyfeed.news_list import NewsList
from lazyfeed.repositories import FeedRepository, PostRepository


class LazyFeedApp(App):
    """
    A Textual based application to read RSS feeds in
    the terminal.
    """

    TITLE = "lazyfeed"
    CSS_PATH = "global.tcss"

    BINDINGS = [
        ("?", "display_help", "Display Help Message"),
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle Dark Mode"),
    ]

    def __init__(self, session: Session, client: httpx.AsyncClient, *args, **kwargs):
        super().__init__(*args, **kwargs)

        __session = session
        self.feeds_repository = FeedRepository(__session)
        self.post_repository = PostRepository(__session)

        self.client = client

    def compose(self) -> ComposeResult:
        yield NewsList()

    def action_display_help(self) -> None:
        self.push_screen(HelpModal())

    def on_mount(self) -> None:
        self.news_list = self.query_one(NewsList)

    async def on_news_list_ready(self, _: NewsList.Ready) -> None:
        self.fetch_posts()

    @work()
    async def fetch_posts(self) -> None:
        feeds = self.feeds_repository.get_all()
        if not len(feeds):
            self.notify("You don't have any feeds!")
            return

        pending_posts = self.post_repository.get_by_attributes(readed=False)
        for post in pending_posts:
            self.news_list.mount_post(post)

        new_posts = []
        for feed in feeds:
            try:
                entries, etag = await fetch_feed(self.client, feed)
                if etag:
                    self.feeds_repository.update(feed.id, etag=etag)
            except Exception:
                self.notify(
                    f"Error while fetching {feed.url}.",
                    severity="error",
                )
                continue

            for entry in entries:
                posts_in_db = self.post_repository.get_by_attributes(url=entry.link)
                if posts_in_db:
                    continue

                new_posts.append(
                    Post(
                        feed=feed,
                        url=entry.link,
                        title=entry.title,
                        summary=entry.summary,
                    )
                )

        for post in new_posts:
            try:
                post_content = await fetch_post(self.client, post.url)
                post.content = post_content

                self.post_repository.add(post)
                self.news_list.mount_post(post)
            except Exception:
                self.notify(
                    f"Error while trying to fetch {post.url}",
                    severity="error",
                )
                continue


if __name__ == "__main__":
    engine = create_engine("sqlite:///lazyfeed.db")
    init_db(engine)

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    client = httpx.AsyncClient(
        timeout=10,
        follow_redirects=True,
        limits=limits,
    )
    with Session(engine) as session:
        app = LazyFeedApp(session, client)
        app.run()
