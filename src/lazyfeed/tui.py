from sqlalchemy.orm import Session
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer


class LazyFeedApp(App):
    """
    A Textual based application to read RSS feeds in
    the terminal.
    """

    TITLE = "lazyfeed"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    def __init__(self, session: Session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
