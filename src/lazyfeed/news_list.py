from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.reactive import var
from textual.widgets import Label, ListItem, ListView
from lazyfeed.models import Post


class NewsListItem(ListItem):
    def __init__(self, idx: int, post: Post, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.idx = idx
        self.post = post

    def compose(self) -> ComposeResult:
        yield Label(f"{str(self.idx)}. [{self.post.feed.title}] {self.post.title}")


class NewsList(ListView):
    class Ready(Message):
        pass

    class MarkItemAsReaded(Message):
        def __init__(self, post_id: int) -> None:
            self.post_id = post_id
            super().__init__()

    number_posts: var[int] = var(0)

    BINDINGS = ListView.BINDINGS + [
        Binding("k", "cursor_up", "Cursor Up", show=False),
        Binding("j", "cursor_down", "Cursor Down", show=False),
        Binding("o", "select_cursor", "Open In Browser", show=False),
        Binding("x", "mark_as_read", "Mark Item As Read", show=False),
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

        self.post_message(self.MarkItemAsReaded(post.id))

    def action_mark_as_read(self) -> None:
        if not self.highlighted_child:
            return

        self.pop(self.index)
        self.post_message(self.MarkItemAsReaded(self.highlighted_child.post.id))

    def mount_post(self, post: Post) -> None:
        self.mount(
            NewsListItem(
                self.number_posts + 1,
                post,
            )
        )
        self.number_posts += 1
