from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Label, Static


class CustomHeader(Static):
    """
    Custom header widget displaying a title and subtitle.
    """

    def __init__(self, title: str, subtitle: str) -> None:
        self.title = title
        self.subtitle = subtitle
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label(self.title, classes="header__title"),
            Label(self.subtitle, classes="header__subtitle"),
        )
