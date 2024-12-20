from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import MarkdownViewer, Footer
from lazyfeed.messages import OpenInBrowser, SaveForLater
from lazyfeed.models import Item


class ItemScreen(Screen):
    """
    Screen for displaying the content of a single item in markdown format.
    """

    BINDINGS = [
        Binding("R", "none", "none", show=False, priority=True),
        Binding("ctrl+c,escape,q,o", "app.pop_screen", "go back", priority=True),
        Binding("s", "save_for_later", "save", priority=True),
        Binding("O", "open_in_browser", "open in browser", priority=True),
    ]

    def __init__(self, item: Item):
        super().__init__()
        self.item = item

    def compose(self) -> ComposeResult:
        yield MarkdownViewer(self.item.content, show_table_of_contents=False)
        yield Footer()

    def on_mount(self) -> None:
        self.md_viewer = self.query_one(MarkdownViewer)
        self.md_viewer.border_title = "article"

    def action_open_in_browser(self) -> None:
        self.post_message(OpenInBrowser(self.item.id))

    def action_save_for_later(self) -> None:
        self.post_message(SaveForLater(self.item.id))

    def action_none(self) -> None:
        pass
