from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.validation import Function
from textual.widgets import Button, Input, Label
from textual.screen import ModalScreen
from lazyfeed.messages import EditFeed
from lazyfeed.widgets.validators import is_valid_url


class EditFeedModal(ModalScreen[None]):
    BINDINGS = [
        ("escape", "dismiss", "dismiss"),
    ]

    def __init__(self, url: str, title: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.url = url
        self.title = title

    def compose(self) -> ComposeResult:
        yield Container(
            Label("feed title"),
            Input(
                placeholder="title (optional)",
                classes="input--feed-title",
                value=self.title,
            ),
        )
        yield Container(
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
        )
        yield Button(label="edit feed")

    def on_mount(self) -> None:
        self.border_title = "edit feed"
        self.button = self.query_one(Button)

    def action_dismiss_overlay(self) -> None:
        self.dismiss(None)

    @on(Input.Changed, ".input--feed-url")
    def enable_button(self, event: Input.Changed) -> None:
        if not event.value or not event.validation_result.is_valid:
            self.button.disabled = True
            return

        self.button.disabled = False

    # TODO: submit form after validating all inputs
    # @on(Button.Pressed)
    # def submit_form(self) -> None:
    #     pass

    @on(Input.Submitted, ".input--feed-url")
    async def edit_feed(self, event: Input.Submitted) -> None:
        if not event.validation_result.is_valid:
            return

        self.post_message(
            EditFeed(
                event.value,
                self.query_one(".input--feed-title").value,
            )
        )
        self.dismiss()
