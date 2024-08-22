from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widgets import Label, ListItem, ListView
from lazyfeed.confirm_modal import ConfirmModal
from lazyfeed.models import Post


class NewsListItem(ListItem):
    def __init__(self, post: Post, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.post = post

    def compose(self) -> ComposeResult:
        yield Label(f"[{self.post.feed.title}] {self.post.title}")


class NewsList(ListView):
    BINDINGS = ListView.BINDINGS + [
        Binding("k", "cursor_up", "Cursor Up", show=False),
        Binding("j", "cursor_down", "Cursor Down", show=False),
        Binding("o", "select_cursor", "Open In Browser", show=False),
        Binding("x", "mark_as_read", "Mark Item As Read", show=False),
        Binding("A", "mark_all_as_read", "Mark All As Read", show=False),
    ]

    def on_mount(self) -> None:
        self.border_title = self.app.TITLE
        self.border_subtitle = "↑/k up · ↓/j down · o open · q quit · ? help"
        self.post_message(self.Ready())

    @on(ListView.Selected)
    def open_in_browser(self) -> None:
        if not self.highlighted_child:
            return

        post = self.highlighted_child.post
        assert post is not None

        self.app.open_url(post.url)
        self.pop(self.index)

        self.post_message(self.MarkItemAsRead(post.id))

    def action_mark_as_read(self) -> None:
        if not self.highlighted_child:
            return

        self.pop(self.index)
        self.post_message(self.MarkItemAsRead(self.highlighted_child.post.id))

    def action_mark_all_as_read(self) -> None:
        def check_confirmation(response: bool | None) -> None:
            if response:
                self.clear()
                self.post_message(self.MarkAllItemsAsRead())

        self.app.push_screen(
            ConfirmModal('Are you sure that you want to mark all items as "readed"?'),
            check_confirmation,
        )

    def mount_post(self, post: Post) -> None:
        self.mount(NewsListItem(post))

    class Ready(Message):
        pass

    class MarkItemAsRead(Message):
        def __init__(self, post_id: int) -> None:
            super().__init__()
            self.post_id = post_id

    class MarkAllItemsAsRead(Message):
        pass
