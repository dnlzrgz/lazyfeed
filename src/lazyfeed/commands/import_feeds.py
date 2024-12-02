# import asyncio
from sqlalchemy.orm import Session
import rich_click as click
from lazyfeed.utils import import_opml


@click.command(
    name="import",
    help="Import RSS feeds from an OPML file.",
)
@click.argument("input", type=click.File("rb"))
@click.pass_context
def import_feeds(ctx, input) -> None:
    engine = ctx.obj["engine"]
    settings = ctx.obj["settings"]
    with Session(engine) as session:
        urls = import_opml(input)
        # asyncio.run(_add_feeds(session, settings, urls))
