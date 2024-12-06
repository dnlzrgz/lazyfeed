from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.validation import Function
from textual.widgets import Button, Input, Label
from textual.screen import ModalScreen
from lazyfeed.messages import NewFeed
from lazyfeed.widgets.validators import is_valid_url


class AddFeedModal(ModalScreen[None]):
    BINDINGS = [
        ("escape", "dismiss", "dismiss"),
    ]

    def compose(self) -> ComposeResult:
        yield Container(
            Label("feed title"),
            Input(
                placeholder="title (optional)",
                classes="input--feed-title",
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
            ),
        )
        yield Button(label="add feed", disabled=True)

    def on_mount(self) -> None:
        self.border_title = "add new feed"
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

    # TODO: submit form after validating all inputs
    # @on(Button.Pressed)
    # def submit_form(self) -> None:
    #     pass

    @on(Input.Submitted, ".input--feed-url")
    async def add_new_feed(self, event: Input.Submitted) -> None:
        if not event.validation_result.is_valid:
            return

        self.post_message(
            NewFeed(
                event.value,
                self.query_one(".input--feed-title").value,
            )
        )
        self.dismiss()
