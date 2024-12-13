from textual.binding import Binding
from textual.widgets import Tree
from lazyfeed.messages import DeleteFeed
from lazyfeed.models import Feed
from lazyfeed.widgets.modals import AddFeedModal, ConfirmActionModal, EditFeedModal


class RSSFeedTree(Tree):
    BINDINGS = [
        Binding("backspace,d,x", "delete", "delete feed"),
        Binding("a,n", "add", "add new feed"),
        Binding("e", "edit", "edit feed"),
        Binding("up,k", "cursor_up", "cursor Up", show=False),
        Binding("down,j", "cursor_down", "cursor down", show=False),
        Binding("g", "scroll_home", "cursor to top", show=False),
        Binding("G", "scroll_end", "cursor to bottom", show=False),
    ]

    def on_mount(self) -> None:
        self.show_root = False
        self.border_title = "feeds"

    def action_delete(self) -> None:
        if not self.cursor_node or not self.cursor_node.data:
            self.notify("no feed selected.")
            return

        feed_name = self.cursor_node.data.get("url", self.cursor_node.label)

        def callback(confirmation: bool | None = False) -> None:
            if confirmation:
                self.post_message(DeleteFeed(feed_name))

        self.app.push_screen(
            ConfirmActionModal(
                message=f"are you sure you want to delete '{feed_name}'?",
                action_name="delete",
            ),
            callback,
        )

    def action_add(self) -> None:
        self.app.push_screen(AddFeedModal())

    def action_edit(self) -> None:
        self.app.push_screen(
            EditFeedModal(
                id=self.cursor_node.data["id"],
                url=self.cursor_node.data["url"],
                title=self.cursor_node.label,
            )
        )

    def mount_feeds(self, feeds: list[Feed]) -> None:
        self.loading = True
        self.clear()

        self.guide_depth = 3
        self.root.expand()

        for feed in feeds:
            self.root.add_leaf(label=feed.title, data={"id": feed.id, "url": feed.url})

        self.cursor_line = 0
        self.loading = False
