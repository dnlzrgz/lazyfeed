from textual.binding import Binding
from textual.widgets import Tree
from lazyfeed.messages import AddFeed, DeleteFeed, EditFeed, FilterByFeed
from lazyfeed.widgets.helpable import HelpData


class RSSFeedTree(Tree):
    help = HelpData(title="rss feed tree")

    BINDINGS = [
        Binding("backspace,d,x", "delete", "delete feed"),
        Binding("a,n", "add", "add feed"),
        Binding("e", "edit", "edit feed"),
        Binding("enter", "select_feed", "select feed"),
        Binding("up,k", "cursor_up", "cursor up", show=False),
        Binding("down,j", "cursor_down", "cursor down", show=False),
        Binding("g", "scroll_home", "cursor to top", show=False),
        Binding("G", "scroll_end", "cursor to bottom", show=False),
    ]

    def on_mount(self) -> None:
        self.show_root = False
        self.border_title = "feeds"

    def action_delete(self) -> None:
        if not self.cursor_node or not self.cursor_node.data:
            self.notify("no feed selected")
            return

        self.post_message(DeleteFeed(self.cursor_node.data["id"]))

    def action_add(self) -> None:
        self.post_message(AddFeed())

    def action_edit(self) -> None:
        if not self.cursor_node or not self.cursor_node.data:
            self.notify("no feed selected")
            return

        self.post_message(EditFeed(id=self.cursor_node.data["id"]))

    def action_select_feed(self) -> None:
        if not self.cursor_node or not self.cursor_node.data:
            self.notify("no feed selected")
            return

        self.post_message(FilterByFeed(id=self.cursor_node.data["id"]))

    def mount_feeds(self, feeds: list[tuple[int, str]]) -> None:
        self.loading = True
        self.clear()

        self.guide_depth = 3
        self.root.expand()

        for feed in feeds:
            self.root.add_leaf(label=feed[1], data={"id": feed[0]})

        self.cursor_line = 0
        self.loading = False
