from sqlalchemy.orm import Session
import rich_click as click
from lazyfeed.utils import console, export_opml
from lazyfeed.repositories import FeedRepository


@click.command(
    name="export",
    help="Export all RSS feeds to an OPML file.",
)
@click.argument(
    "output",
    type=click.File("wb"),
    default="lazyfeed.opml",
)
@click.pass_context
def export_feeds(ctx, output) -> None:
    engine = ctx.obj["engine"]
    with Session(engine) as session:
        feed_repository = FeedRepository(session)
        feeds = feed_repository.get_all()

        if not len(feeds):
            console.print("[red]ERR[/] Add some feeds first!")
            return

        export_opml(feeds, output)
