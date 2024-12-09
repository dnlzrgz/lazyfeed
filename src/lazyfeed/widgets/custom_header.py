from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Label, Static


class CustomHeader(Static):
    def __init__(self, app_name: str, version: str) -> None:
        self.app_name = app_name
        self.version = version
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label(f"↪ {self.app_name}", classes="header__title"),
            Label(f"v{self.version}", classes="header__version"),
        )
