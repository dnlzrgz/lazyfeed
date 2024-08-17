import webbrowser
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Label, ListItem, ListView
from lazyfeed.db import init_db

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


class NewsListItem(ListItem):
    def __init__(
        self, idx: int, site: str, title: str, url: str, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.idx = idx
        self.site = site
        self.title = title
        self.url = url

    def compose(self) -> ComposeResult:
        yield Label(f"{str(self.idx).rjust(3, ' ')}. [{self.site}] {self.title}")


class NewsList(ListView):
    BINDINGS = ListView.BINDINGS + [
        Binding("k", "cursor_up", "Cursor Up", show=False),
        Binding("j", "cursor_down", "Cursor Down", show=False),
        Binding("o", "select_cursor", "Open In Browser", show=False),
    ]

    def __init__(self, news, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.news = news

    def compose(self) -> ComposeResult:
        for i, item in enumerate(news):
            yield NewsListItem(
                idx=i, site=item[0], title=item[1], url=f"https://localhost:800{i}"
            )

    def on_mount(self) -> None:
        self.border_title = self.app.TITLE
        self.border_subtitle = "↑/k up · ↓/j down · o open · q quit · ? help"

    def on_list_view_selected(self, message: ListView.Selected) -> None:
        self.pop(self.index)
        webbrowser.open(message.item.url)


class LazyFeedApp(App):
    """
    A Textual based application to read RSS feeds in
    the terminal.
    """

    TITLE = "lazyfeed"
    CSS_PATH = "global.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    def __init__(self, session: Session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

    def compose(self) -> ComposeResult:
        yield NewsList(news)


if __name__ == "__main__":
    engine = create_engine("sqlite:///layfeed.db")
    init_db(engine)

    with Session(engine) as session:
        app = LazyFeedApp(session)
        app.run()
