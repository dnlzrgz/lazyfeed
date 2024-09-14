import time
from textual import events
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import DataTable


class Tabloid(DataTable):
    def __init__(self, *args, **kwargs):
        super().__init__(cursor_type="row", header_height=0, *args, **kwargs)

    BINDINGS = DataTable.BINDINGS + [
        Binding("A", "mark_all_as_read", "Mark All As Read", show=False),
        Binding("G", "scroll_bottom", "Bottom", show=False),
        Binding("j", "cursor_down", "Cursor Down", show=False),
        Binding("k", "cursor_up", "Cursor Up", show=False),
        Binding("n", "cursor_down", "Cursor Down", show=False),
        Binding("p", "cursor_up", "Cursor Up", show=False),
        Binding("o", "select_cursor", "Open In Browser", show=False),
        Binding("m", "mark_as_read", "Mark Post As Read", show=False),
    ]

    first_key_pressed: reactive[str | None] = reactive(None)

    def on_mount(self) -> None:
        self.add_column("s", key="saved")
        self.add_column("f", key="fav")
        self.add_column("t", key="title")

        self.border_title = self.app.TITLE
        self.border_subtitle = "↑/k up · ↓/j down · o open · q quit · ? help"

    def action_select_cursor(self) -> None:
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            self.post_message(self.OpenPost(int(row_key.value)))
        except Exception:
            pass

    def action_mark_as_read(self) -> None:
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            self.post_message(self.MarkPostAsRead(int(row_key.value)))
        except Exception:
            pass

    def action_mark_all_as_read(self) -> None:
        self.post_message(self.MarkAllPostsAsRead())

    def action_save_for_later(self) -> None:
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            self.post_message(self.SavePost(int(row_key.value)))
        except Exception:
            pass

    def action_mark_as_fav(self) -> None:
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            self.post_message(self.MarkPostAsFav(int(row_key.value)))
        except Exception:
            pass

    async def on_key(self, event: events.Key) -> None:
        if event.key == "g":
            if self.first_key_pressed == "g":
                self.action_scroll_top()
                self.first_key_pressed = None
            else:
                self.first_key_pressed = "g"
                self.first_key_time = time.time()
        elif self.first_key_pressed == "g":
            if time.time() - self.first_key_time < 0.5:
                action_map = {
                    "l": self.LoadSavedPosts,
                    "f": self.LoadFavPosts,
                    "p": self.LoadAllNewPosts,
                    "n": self.LoadAllNewPosts,
                    "a": self.LoadAllPosts,
                }
                action = action_map.get(event.key)
                if action:
                    self.post_message(action())

            self.first_key_pressed = None
        elif event.key == "f":
            self.action_mark_as_fav()
            self.first_key_pressed = None
        elif event.key == "s":
            self.action_save_for_later()
            self.first_key_pressed = None
        else:
            self.first_key_pressed = None

    class LoadAllPosts(Message):
        pass

    class LoadAllNewPosts(Message):
        pass

    class LoadSavedPosts(Message):
        pass

    class LoadFavPosts(Message):
        pass

    class OpenPost(Message):
        def __init__(self, post_id: int) -> None:
            super().__init__()
            self.post_id = post_id

    class MarkPostAsRead(Message):
        def __init__(self, post_id: int) -> None:
            super().__init__()
            self.post_id = post_id

    class MarkAllPostsAsRead(Message):
        pass

    class SavePost(Message):
        def __init__(self, post_id: int) -> None:
            super().__init__()
            self.post_id = post_id

    class MarkPostAsFav(Message):
        def __init__(self, post_id: int) -> None:
            super().__init__()
            self.post_id = post_id
