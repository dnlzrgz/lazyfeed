from textual.binding import Binding
from textual.widgets import DataTable
from lazyfeed.models import Item


class ItemsTable(DataTable):
    def __init__(self, *args, **kwargs):
        super().__init__(cursor_type="row", header_height=0, *args, **kwargs)

    BINDINGS = [
        Binding("up,k", "cursor_up", "cursor Up", show=False),
        Binding("down,j", "cursor_down", "cursor down", show=False),
        Binding("g", "scroll_home", "cursor to top", show=False),
        Binding("G", "scroll_end", "cursor to bottom", show=False),
    ]

    def on_mount(self) -> None:
        self.add_column("t", key="title")
        self.border_title = "items"

    def mount_items(self, items: list[Item]) -> None:
        self.loading = True
        self.clear()

        for item in items:
            self.add_row(item.title or item.url)

        self.loading = False
