from typing import Tuple, List
from rich.text import Text
from textual.binding import Binding
from textual.widgets import Tree
from lazyfeed.messages import AddFeed, DeleteFeed, EditFeed, FilterByFeed
from lazyfeed.widgets.helpable import HelpData


class RSSFeedTree(Tree):
    """
    Custom Tree that provides functionality to show, add, edit, delete and filter
    by feeds.
    """

    help = HelpData(
        title="rss feed tree",
        description="""\
A tree for managing RSS feeds. You can (`a`)dd new feeds, (`e`)dit an existing feed, 
(`d`)elete feeds, or select one to filter the items (`enter`).
""",
    )

    BINDINGS = [
        Binding("backspace,d,x", "delete", "delete feed"),
        Binding("a,n", "add", "add"),
        Binding("e", "edit", "edit"),
        Binding("enter", "select_feed", "select"),
        Binding("up,k", "cursor_up", "cursor up", show=False),
        Binding("down,j", "cursor_down", "cursor down", show=False),
        Binding("g", "scroll_home", "cursor to top", show=False),
        Binding("G", "scroll_end", "cursor to bottom", show=False),
    ]

    def on_mount(self) -> None:
        self.show_root = False
        self.border_title = "feeds"

        css_variables = self.app.get_css_variables()
        self.primary = css_variables.get("primary", "blue")

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

    def update_feed(self, feed_data: Tuple[int, int, str]) -> None:
        feed_id, pending_posts, title = feed_data
        for node in self.root.children:
            if node.data and node.data["id"] == feed_id:
                label = Text()
                if pending_posts:
                    label.append(f"{pending_posts}", style=f"on {self.primary}")
                    label.append(" ")

                label.append(title)

                node.label = label
                self.refresh()
                return

    def mount_feeds(self, feeds_data: List[Tuple[int, int, str]]) -> None:
        self.clear()
        self.guide_depth = 3
        self.root.expand()

        for feed in feeds_data:
            feed_id, pending_posts, title = feed
            label = Text()
            if pending_posts:
                label.append(f"{pending_posts}", style=f"on {self.primary}")
                label.append(" ")

            label.append(title)

            self.root.add_leaf(label=label, data={"id": feed_id})

        self.cursor_line = 0
