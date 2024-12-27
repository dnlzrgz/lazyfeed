from textual.message import Message


class AddFeed(Message):
    """Message to add a new RSS feed."""

    pass


class EditFeed(Message):
    """Message to edit an existing RSS feed."""

    def __init__(self, id: int) -> None:
        self.id = id
        super().__init__()


class DeleteFeed(Message):
    """Message to delete a specified RSS feed."""

    def __init__(self, id: int) -> None:
        self.id = id
        super().__init__()


class FilterByFeed(Message):
    """Message to filter by the specified RSS feed."""

    def __init__(self, id: int) -> None:
        self.id = id
        super().__init__()


class MarkAsRead(Message):
    """Message to mark an item as 'read'."""

    def __init__(self, item_id: int) -> None:
        self.item_id = item_id
        super().__init__()


class MarkAllAsRead(Message):
    """Message to mark all items as 'read'."""

    pass


class MarkAsPending(Message):
    """Message to mark an item as 'unread' or 'pending'."""

    def __init__(self, item_id: int) -> None:
        self.item_id = item_id
        super().__init__()


class Open(Message):
    """Message to open item's content."""

    def __init__(self, item_id: int) -> None:
        self.item_id = item_id
        super().__init__()


class OpenInBrowser(Message):
    """Message to open an item in the browser."""

    def __init__(self, item_id: int) -> None:
        self.item_id = item_id
        super().__init__()


class SaveForLater(Message):
    """Message to save an item for later."""

    def __init__(self, item_id: int) -> None:
        self.item_id = item_id
        super().__init__()


class ShowPending(Message):
    """Message to list all items."""

    pass


class ShowAll(Message):
    """Message to list all pending items."""

    pass


class ShowSavedForLater(Message):
    """Message to list all saved for later items."""

    pass


class ShowToday(Message):
    """Message to list all items published at today's date."""

    pass
