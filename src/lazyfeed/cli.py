import asyncio
import os
import click
import httpx
from sqlalchemy import create_engine, exc, text
from sqlalchemy.orm import Session
from rich.console import Console
from lazyfeed.db import init_db
from lazyfeed.feeds import fetch_feed_metadata
from lazyfeed.opml_utils import export_opml, import_opml
from lazyfeed.repositories import FeedRepository
from lazyfeed.tui import LazyFeedApp

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx) -> None:
    """
    A modern RSS feed reader for the terminal.
    """

    ctx.ensure_object(dict)

    # Check app config directory.
    app_dir = click.get_app_dir(app_name="lazyfeed")
    if not os.path.exists(app_dir):
        os.makedirs(app_dir)

    ctx.obj["app_dir_path"] = app_dir

    # Set up the SQLite database engine.
    sqlite_url = f"sqlite:///{os.path.join(app_dir, "db.sqlite3")}"
    engine = create_engine(sqlite_url)
    init_db(engine)
    ctx.obj["engine"] = engine

    # Create async httpx client.
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    client = httpx.AsyncClient(
        timeout=10,
        follow_redirects=True,
        limits=limits,
    )
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
    with console.status(
        "Fetching feeds... This will only take a moment!",
        spinner="earth",
    ):
        for url in urls:
            feeds_in_db = feed_repository.get_by_attributes(url=url)
            if feeds_in_db:
                console.print(
                    f"[bold yellow]Warning:[/bold yellow]: Feed '{url}' already added!"
                )
                continue

            try:
                feed = await fetch_feed_metadata(client, url)
                feed_in_db = feed_repository.add(feed)
                console.print(
                    f"[bold green]Success:[/bold green] Added RSS feed for '{feed_in_db.title}' ({feed_in_db.url})"
                )
            except Exception:
                console.print(
                    f"[bold red]Error:[/bold red] While fetching '{url}' something bad happened!"
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
                "[bold red]Error:[/bold red] You need to add some feeds first!"
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
                "[bold green]Success:[/bold green] Unused space has been reclaimed!"
            )
        except exc.SQLAlchemyError as e:
            console.print(f"[bold red]Error:[/bold red] Something went wrong: {e}!")
