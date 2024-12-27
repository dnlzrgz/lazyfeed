from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.validation import Function
from textual.widgets import Button, Input, Label
from textual.screen import ModalScreen
from lazyfeed.widgets.validators import is_valid_url


class AddFeedModal(ModalScreen[dict | None]):
    """
    Modal screen for adding a new RSS feed.
    """

    BINDINGS = [
        ("escape,q", "dismiss", "dismiss"),
    ]

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="modal-body modal-body--add") as container:
            container.border_title = "add new feed"

            yield Container(
                Container(
                    Label("title (optional)"),
                    Input(
                        placeholder="title",
                        classes="input--feed-title",
                    ),
                ),
                Container(
                    Label("url"),
                    Input(
                        placeholder="url",
                        validate_on=["changed", "submitted"],
                        validators=[
                            Function(is_valid_url, "invalid url."),
                        ],
                        classes="input--feed-url",
                    ),
                ),
                classes="inputs",
            )
            yield Button(label="add feed", variant="success", disabled=True)

    def on_mount(self) -> None:
        self.input_fields = self.query(Input)
        self.button = self.query_one(Button)

    def action_dismiss_overlay(self) -> None:
        self.dismiss(None)

    @on(Input.Changed, ".input--feed-url")
    def enable_button(self, event: Input.Changed) -> None:
        if not event.value or not event.validation_result.is_valid:
            self.button.disabled = True
            return

        self.button.disabled = False

    @on(Button.Pressed)
    def submit_form(self) -> None:
        self.dismiss(
            {
                "title": self.query_one(".input--feed-title").value,
                "url": self.query_one(".input--feed-url").value,
            }
        )

    @on(Input.Submitted, ".input--feed-url")
    async def add_new_feed(self, event: Input.Submitted) -> None:
        if not event.validation_result.is_valid:
            return

        self.dismiss(
            {
                "title": self.query_one(".input--feed-title").value,
                "url": event.value,
            }
        )
