from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from textual.app import App, ComposeResult
from textual.reactive import reactive, var
from lazyfeed.news_list import NewsList
from lazyfeed.db import init_db
from lazyfeed.models import Feed, Post
from lazyfeed.repositories import FeedRepository, PostRepository
from lazyfeed.help_modal import HelpModal

news = [
    (
        "Galactic News Network",
        "42: The Ultimate Answer to Life, the Universe, and Everything",
    ),
    (
        "Interstellar Tech Digest",
        "The Rise of Sentient AI: A Guide for the Perplexed",
    ),
    (
        "Hitchhiker's Guide to the Galaxy",
        "Don't Panic: Essential Tips for Space Travel",
    ),
    (
        "Cosmic Innovations",
        "Teleportation: The Future of Intergalactic Commutes",
    ),
    (
        "Zaphod's Tech Blog",
        "Two Heads Are Better Than One: The Benefits of Dual Consciousness",
    ),
    (
        "Pan Galactic Gargle Blaster Reviews",
        "Top 10 Drinks for the Intergalactic Traveler",
    ),
    (
        "Deep Space Exploration",
        "The Search for Extraterrestrial Life: Are We Alone?",
    ),
    (
        "The Galactic Federation",
        "New Regulations on Time Travel: What You Need to Know",
    ),
    (
        "Robot Rights Watch",
        "The Ethical Implications of AI in Society",
    ),
    (
        "The Vogon Poetry Society",
        "Why Poetry is the Most Advanced Form of Communication",
    ),
]


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

    loading: reactive[bool] = reactive(False, recompose=True)
    feeds: var[list[Feed] | None] = var([])
    news: var[list[Post] | None] = var([])

    def __init__(self, session: Session, *args, **kwargs):
        super().__init__(*args, **kwargs)

        __session = session
        self.feeds_repository = FeedRepository(__session)
        self.post_repository = PostRepository(__session)

        self.news_list = NewsList([])

    def compose(self) -> ComposeResult:
        yield self.news_list

    def action_display_help(self) -> None:
        self.push_screen(HelpModal())

    def on_mount(self) -> None:
        # TODO: load "loading" widget
        # TODO: load feeds
        # TODO: fetch new posts
        # TODO: unmount "loading" widget
        # TODO: mount NewsList
        pass


if __name__ == "__main__":
    engine = create_engine("sqlite:///layfeed.db")
    init_db(engine)

    with Session(engine) as session:
        app = LazyFeedApp(session)
        app.run()
