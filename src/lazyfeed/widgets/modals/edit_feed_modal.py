from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.validation import Function
from textual.widgets import Button, Input, Label
from textual.screen import ModalScreen
from lazyfeed.widgets.validators import is_valid_url


class EditFeedModal(ModalScreen[dict | None]):
    """
    Modal screen for editing an existing RSS feed.
    """

    BINDINGS = [
        ("escape,q", "dismiss", "dismiss"),
    ]

    def __init__(self, url: str, title: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.url = url
        self.title = title

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="modal-body") as container:
            container.border_title = "edit feed"

            yield Container(
                Container(
                    Label("feed title"),
                    Input(
                        placeholder="title (optional)",
                        classes="input--feed-title",
                        value=self.title,
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
                        value=self.url,
                    ),
                ),
                classes="inputs",
            )
            yield Button(label="update", variant="success")

    def on_mount(self) -> None:
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
    async def edit_feed(self, event: Input.Submitted) -> None:
        if not event.validation_result.is_valid:
            return

        self.dismiss(
            {
                "title": self.query_one(".input--feed-title").value,
                "url": event.value,
            }
        )
