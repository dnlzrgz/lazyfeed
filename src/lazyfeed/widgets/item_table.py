from textual.binding import Binding
from textual.widgets import DataTable
from lazyfeed.models import Item
from lazyfeed.messages import (
    MarkAllAsRead,
    MarkAsRead,
    Open,
    OpenInBrowser,
    SaveForLater,
    ShowAll,
    ShowSavedForLater,
)


class ItemTable(DataTable):
    def __init__(self, *args, **kwargs):
        super().__init__(cursor_type="row", header_height=0, *args, **kwargs)

    BINDINGS = [
        Binding("up,k", "cursor_up", "cursor up", show=False),
        Binding("down,j", "cursor_down", "cursor down", show=False),
        Binding("g", "scroll_top", "cursor to top", show=False),
        Binding("G", "scroll_bottom", "cursor to bottom", show=False),
        Binding("o", "open", "open"),
        Binding("O", "open_in_browser", "open in browser"),
        Binding("m", "mark_as_read", "mark as read"),
        Binding("M", "mark_all_as_read", "mark all as read", show=False),
        Binding("s", "save_for_later", "save"),
        Binding("a", "show_all", "show all"),
        Binding("l", "show_saved", "show saved"),
    ]

    def on_mount(self) -> None:
        self.add_column("items", key="items")
        self.border_title = "items"

    def action_mark_as_read(self) -> None:
        row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)

        assert row_key.value
        self.post_message(MarkAsRead(int(row_key.value)))

    def action_mark_all_as_read(self) -> None:
        self.post_message(MarkAllAsRead())

    def action_open(self) -> None:
        row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)

        assert row_key.value
        self.post_message(Open(int(row_key.value)))

    def action_open_in_browser(self) -> None:
        row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)

        assert row_key.value
        self.post_message(OpenInBrowser(int(row_key.value)))

    def action_save_for_later(self) -> None:
        row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)

        assert row_key.value
        self.post_message(SaveForLater(int(row_key.value)))

    def action_show_all(self) -> None:
        self.post_message(ShowAll())

    def action_show_saved(self) -> None:
        self.post_message(ShowSavedForLater())

    def format_item(self, item: Item) -> str:
        saved = "" if item.is_saved else " "
        item_title = item.title or item.url
        url = item.url

        return f"{saved} [bold]{item_title}[/] ([underline italic]{url}[/])"

    def update_item(self, row_key: str, item: Item) -> None:
        self.update_cell(row_key, "items", self.format_item(item))

    def mount_items(self, items: list[Item]) -> None:
        self.loading = True
        self.clear()

        for item in items:
            self.add_row(self.format_item(item), key=f"{item.id}")

        self.border_subtitle = f"{len(items)}"
        self.loading = False
