from textual import on
from textual.app import ComposeResult
from textual.widgets import Button, Static
from textual.screen import ModalScreen


class ConfirmActionModal(ModalScreen[bool]):
    BINDINGS = [
        ("escape", "dismiss", "dismiss"),
        ("enter", "confirm", "confirm"),
    ]

    def __init__(self, message: str, action_name: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.message = message
        self.action_name = action_name

    def compose(self) -> ComposeResult:
        yield Static(self.message)
        yield Button(label=self.action_name)

    def on_mount(self) -> None:
        self.border_title = "delete feed"

    def action_dismiss_overlay(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed)
    def action_confirm(self) -> None:
        self.dismiss(True)
