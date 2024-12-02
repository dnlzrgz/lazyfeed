import rich_click as click
from lazyfeed.tui import LazyFeedApp


@click.command(
    name="tui",
    help="Start the TUI.",
)
@click.pass_context
def start_tui(ctx) -> None:
    settings = ctx.obj["settings"]
    app = LazyFeedApp(settings)
    app.run()
