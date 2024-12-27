from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import DataTable, Label, Markdown
from lazyfeed.widgets.helpable import Helpable


class HelpModal(ModalScreen[None]):
    """
    Modal screen to display help information for a specific widget.
    """

    BINDINGS = [
        ("escape,q", "dismiss", "dismiss"),
    ]

    def __init__(self, widget: Widget) -> None:
        super().__init__()
        self.widget = widget

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="modal-body modal-body--help") as container:
            widget = self.widget
            if isinstance(widget, Helpable):
                help = widget.help
                help_title = help.title
                help_description = help.description

                if help_title:
                    container.border_title = help_title
                else:
                    container.border_title = "help"

                if help_description:
                    help_description = help_title.strip()
                    with VerticalScroll(classes="help-description"):
                        yield Markdown(help_description)

            bindings = widget._bindings
            keys: list[tuple[str, list[Binding]]] = list(
                bindings.key_to_bindings.items(),
            )

            if keys:
                yield Label("all keybindings", classes="help-table__label")

                table = DataTable(cursor_type="row", zebra_stripes=True)
                table.add_columns("key", "description")
                for _, bindings in keys:
                    table.add_row(
                        Text(
                            ", ".join(
                                binding.key_display
                                if binding.key_display
                                else self.app.get_key_display(binding)
                                for binding in bindings
                            ),
                            style="bold",
                            no_wrap=True,
                            end="",
                        ),
                        bindings[0].description.lower(),
                    )

                yield table
