from pathlib import Path
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Markdown


class HelpModal(ModalScreen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Quit"),
        ("q", "app.pop_screen", "Quit"),
        ("?", "app.pop_screen", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        markdown_path = Path(__file__).parent / "help_modal.md"
        with open(markdown_path, "r") as f:
            markdown = f.read()

        with VerticalScroll(classes="modal modal--help"):
            yield Markdown(markdown=markdown)

    def on_mount(self) -> None:
        self.modal = self.query_one(VerticalScroll)
        self.modal.border_title = "help"
        self.modal.border_subtitle = "q/? quit"
        self.modal.focus()
