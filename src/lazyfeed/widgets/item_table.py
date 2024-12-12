from textual.binding import Binding
from textual.widgets import DataTable
from lazyfeed.models import Item
from lazyfeed.messages import MarkAllAsRead, MarkAsRead
from lazyfeed.widgets.modals.confirm_action_modal import ConfirmActionModal


class ItemTable(DataTable):
    def __init__(self, *args, **kwargs):
        super().__init__(cursor_type="row", header_height=0, *args, **kwargs)

    BINDINGS = [
        Binding("up,k", "cursor_up", "cursor Up", show=False),
        Binding("down,j", "cursor_down", "cursor down", show=False),
        Binding("g", "scroll_top", "cursor to top", show=False),
        Binding("G", "scroll_bottom", "cursor to bottom", show=False),
        Binding("m", "mark_as_read", "mark as read"),
        Binding("M", "mark_all_as_read", "mark all as read"),
        Binding("s", "save", "save for later"),
    ]

    def on_mount(self) -> None:
        self.add_column("saved", key="saved")
        self.add_column("title", key="title")
        self.border_title = "items"

    def action_mark_as_read(self) -> None:
        row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)

        assert row_key.value
        self.post_message(MarkAsRead(int(row_key.value)))

    def action_mark_all_as_read(self) -> None:
        def callback(confirmation: bool | None = False) -> None:
            if confirmation:
                self.post_message(MarkAllAsRead())

        self.app.push_screen(
            ConfirmActionModal(
                message="are you sure you want to mark all items as 'read'?",
                action_name="confirm",
            ),
            callback,
        )

    def mount_items(self, items: list[Item]) -> None:
        self.loading = True
        self.clear()

        for item in items:
            self.add_row(
                "x" if item.is_saved else "", item.title or item.url, key=f"{item.id}"
            )

        self.loading = False
