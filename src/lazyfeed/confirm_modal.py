from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static, Button
from textual.screen import ModalScreen


class ConfirmModal(ModalScreen[bool]):
    BINDINGS = [
        ("escape", "app.pop_screen", "Quit"),
        ("n", "cancel", "Cancel"),
        ("q", "app.pop_screen", "Quit"),
        ("y", "accept", "Accept"),
    ]

    def __init__(self, message: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="modal modal--help"):
            yield Static(self.message)
            yield Horizontal(
                Button(label="(N)o", id="no").focus(),
                Button(label="(Y)es", id="yes"),
                classes="modal__options",
            )

    def on_mount(self) -> None:
        self.modal = self.query_one(".modal")
        self.modal.border_title = "confirm"
        self.modal.border_subtitle = "n cancel · y accept · q quit"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "no":
            self.dismiss(False)
        else:
            self.dismiss(True)

    def action_quit(self) -> None:
        self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_accept(self) -> None:
        self.dismiss(True)
