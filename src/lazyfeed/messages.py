from textual.message import Message


class NewFeed(Message):
    """Message to add a new RSS feed."""

    def __init__(self, url: str, title: str | None = None) -> None:
        self.url = url
        self.title = title
        super().__init__()


class EditFeed(Message):
    """Message to edit existing RSS feed."""

    def __init__(self, feed_id: int, url: str, title: str | None = None) -> None:
        self.feed_id = feed_id
        self.url = url
        self.title = title

        super().__init__()


class DeleteFeed(Message):
    """Message to delete the specified RSS feed."""

    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__()


class MarkAsRead(Message):
    """Message to mark an item as 'read'."""

    def __init__(self, item_id: int) -> None:
        self.item_id = item_id
        super().__init__()


class MarkAllAsRead(Message):
    """Message to mark all items as 'read'."""

    pass


class OpenInBrowser(Message):
    """Message to open an item in the browser."""

    def __init__(self, item_id: int) -> None:
        self.item_id = item_id
        super().__init__()
