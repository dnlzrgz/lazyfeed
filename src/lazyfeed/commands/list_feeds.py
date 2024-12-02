from rich.table import Table
from sqlalchemy.orm import Session
import rich_click as click
from lazyfeed.repositories import FeedRepository
from lazyfeed.utils import console, sqids


@click.command(
    name="list",
    help="Print a list with all your RSS feeds.",
)
@click.pass_context
def list_feeds(ctx):
    engine = ctx.obj["engine"]
    with Session(engine) as session:
        feed_repository = FeedRepository(session)
        feeds = feed_repository.get_all()

        if not len(feeds):
            console.print("[red]ERR[/] Add some feeds first!")
            return

        table = Table(
            show_header=True,
            show_lines=True,
        )
        table.add_column("id", justify="center")
        table.add_column("title", justify="left")

        for feed in feeds:
            table.add_row(
                f"[bold]{sqids.encode([feed.id])}[/]",
                f"[link={feed.link}]{feed.title}[/]",
            )

        console.print(table)
        console.print(
            f"{len(feeds)} feeds",
            highlight=False,
            justify="center",
        )
