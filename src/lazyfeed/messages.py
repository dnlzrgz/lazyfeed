from textual.message import Message


class NewFeed(Message):
    """Message to add a new RSS feed."""

    def __init__(self, url: str, title: str | None = None) -> None:
        self.url = url
        self.title = title
        super().__init__()


class EditFeed(Message):
    """Message to edit existing RSS feed."""

    def __init__(self, url: str, title: str | None = None) -> None:
        self.url = url
        self.title = title
        super().__init__()


class DeleteFeed(Message):
    """Message to delete the specified RSS feed."""

    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__()
