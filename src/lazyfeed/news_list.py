from textual.app import ComposeResult
from textual.binding import Binding
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
    BINDINGS = ListView.BINDINGS + [
        Binding("k", "cursor_up", "Cursor Up", show=False),
        Binding("j", "cursor_down", "Cursor Down", show=False),
        Binding("o", "select_cursor", "Open In Browser", show=False),
    ]

    def __init__(self, news: list[Post], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.news = news

    def compose(self) -> ComposeResult:
        for i, post in enumerate(self.news):
            yield NewsListItem(
                idx=i,
                post=post,
            )

    def on_mount(self) -> None:
        self.border_title = self.app.TITLE
        self.border_subtitle = "↑/k up · ↓/j down · o open · q quit · ? help"

    def on_list_view_selected(self, message: ListView.Selected) -> None:
        self.pop(self.index)
        self.app.open_url(message.item.url)
