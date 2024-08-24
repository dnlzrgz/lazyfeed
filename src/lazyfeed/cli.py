import asyncio
from pathlib import Path
from rich.console import Console
from rich import print
from sqids import Sqids
from sqlalchemy import create_engine, exc, text
from sqlalchemy.orm import Session
import click
import httpx
from lazyfeed.db import init_db
from lazyfeed.feeds import fetch_feed_metadata
from lazyfeed.models import Feed
from lazyfeed.opml_utils import export_opml, import_opml
from lazyfeed.repositories import FeedRepository
from lazyfeed.tui import LazyFeedApp


console = Console()
sqids = Sqids(
    alphabet="e69auyponmz7lk5vtgwi1r23hb0d8jq4xfcs",
    min_length=3,
)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx) -> None:
    """
    A modern RSS feed reader for the terminal.
    """

    ctx.ensure_object(dict)

    # Check app config directory.
    app_dir = Path(click.get_app_dir(app_name="lazyfeed"))
    app_dir.mkdir(parents=True, exist_ok=True)

    ctx.obj["app_dir_path"] = app_dir

    # Set up the SQLite database engine.
    sqlite_url = f"sqlite:///{app_dir / 'lazyfeed.db'}"
    engine = create_engine(sqlite_url)
    init_db(engine)

    ctx.obj["engine"] = engine

    # Create async httpx client.
    client = httpx.AsyncClient(timeout=10, follow_redirects=True)

    ctx.obj["client"] = client

    # If no subcommand, start the TUI.
    if ctx.invoked_subcommand is None:
        ctx.forward(start_tui)


@cli.command(
    name="tui",
    help="Starts the lazyfeed TUI.",
)
@click.pass_context
def start_tui(ctx) -> None:
    engine = ctx.obj["engine"]
    client = ctx.obj["client"]
    with Session(engine) as session:
        app = LazyFeedApp(session, client)
        app.run()


async def _add_feeds(session: Session, client: httpx.AsyncClient, urls: list[str]):
    feed_repository = FeedRepository(session)
    tasks = []

    with console.status(
        "Fetching feeds... This will only take a moment!",
        spinner="earth",
    ):
        for url in urls:
            feeds_in_db = feed_repository.get_by_attributes(url=url)
            if feeds_in_db:
                console.print(
                    f"[bold yellow]WARNING:[/bold yellow]: Feed '{url}' already added!"
                )
                continue

            tasks.append(fetch_feed_metadata(client, url))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                console.print(
                    f"[bold red]ERROR:[/bold red] While fetching '{url}' something bad happened!"
                )
            else:
                assert isinstance(result, Feed)

                feed_in_db = feed_repository.add(result)
                console.print(
                    f"[bold green]SUCCESS:[/bold green] Added RSS feed for '{feed_in_db.title}' ({feed_in_db.url})"
                )

    await client.aclose()


@cli.command(
    name="add",
    help="Add one or more RSS feeds.",
)
@click.argument("urls", nargs=-1)
@click.pass_context
def add_feed(ctx, urls) -> None:
    engine = ctx.obj["engine"]
    client = ctx.obj["client"]
    with Session(engine) as session:
        asyncio.run(_add_feeds(session, client, urls))


@cli.command(
    name="list",
    help="Print a list with all RSS feeds.",
)
@click.pass_context
def list_feeds(ctx):
    engine = ctx.obj["engine"]
    with Session(engine) as session:
        feed_repository = FeedRepository(session)
        feeds = feed_repository.get_all()

        if not len(feeds):
            console.print(
                "[bold red]ERROR:[/bold red] You need to add some feeds first!"
            )
            return

        for feed in feeds:
            print(
                f"- [bold][ {sqids.encode([feed.id])} ][/] '{feed.title}' ( {feed.link} )"
            )


@cli.command(
    name="delete",
    help="Removes feed.",
)
@click.argument("feed_id")
@click.pass_context
def delete_feed(ctx, feed_id):
    engine = ctx.obj["engine"]
    with Session(engine) as session:
        feed_repository = FeedRepository(session)
        decoded_id = sqids.decode(feed_id)[0]
        feed = feed_repository.delete(decoded_id)
        if not feed:
            console.print(
                f"[bold red]ERROR:[/bold red] No feed found with ID '{feed_id}'."
            )
            return

        console.print(
            f"[bold green]SUCCESS:[/bold green] Feed '{feed.title}' deleted correctly!"
        )


@cli.command(
    name="import",
    help="Import RSS feeds from an OPML file.",
)
@click.argument("input", type=click.File("rb"))
@click.pass_context
def import_feeds(ctx, input) -> None:
    engine = ctx.obj["engine"]
    client = ctx.obj["client"]
    with Session(engine) as session:
        urls = import_opml(input)
        asyncio.run(_add_feeds(session, client, urls))


@cli.command(
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
            console.print(
                "[bold red]ERROR:[/bold red] You need to add some feeds first!"
            )
            return

        export_opml(feeds, output)


@cli.command(
    name="vacuum",
    help="Reclaim unused spaced in the database.",
)
@click.pass_context
def vacuum(ctx) -> None:
    engine = ctx.obj["engine"]
    with Session(engine) as session:
        try:
            session.execute(text("VACUUM"))
            session.commit()
            console.print(
                "[bold green]SUCCESS:[/bold green] Unused space has been reclaimed!"
            )
        except exc.SQLAlchemyError as e:
            console.print(f"[bold red]ERROR:[/bold red] Something went wrong: {e}!")
