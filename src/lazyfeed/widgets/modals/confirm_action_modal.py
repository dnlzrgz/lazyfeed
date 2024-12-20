from textual import on
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Button, Static
from textual.screen import ModalScreen


class ConfirmActionModal(ModalScreen[bool]):
    """
    Modal screen with a prompt for confirmation of an action.
    """

    BINDINGS = [
        ("escape,q", "dismiss", "dismiss"),
        ("enter,y", "confirm", "confirm"),
    ]

    def __init__(
        self, border_title: str, message: str, action_name: str, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.border_title = border_title
        self.message = message
        self.action_name = action_name

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="modal-body modal-body--error") as container:
            container.border_title = self.border_title

            yield Static(self.message)
            yield Button(label=self.action_name, variant="error")

    def on_mount(self) -> None:
        self.query_one(Button).focus()

    def action_dismiss_overlay(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed)
    def action_confirm(self) -> None:
        self.dismiss(True)
