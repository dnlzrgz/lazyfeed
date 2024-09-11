import asyncio
import os
import subprocess
from rich import print
from rich.console import Console
from sqids import Sqids
from sqlalchemy import create_engine, exc, text
from sqlalchemy.orm import Session
import aiohttp
import rich_click as click
from lazyfeed.settings import Settings, config_file_path
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

    # Load settings
    settings = Settings()
    ctx.obj["settings"] = settings

    # Set up the SQLite database engine.
    engine = create_engine(settings.app.db_url)
    init_db(engine)

    ctx.obj["engine"] = engine

    # If no subcommand, start the TUI.
    if ctx.invoked_subcommand is None:
        ctx.forward(start_tui)


@cli.command(
    name="tui",
    help="Start the TUI.",
)
@click.pass_context
def start_tui(ctx) -> None:
    engine = ctx.obj["engine"]
    settings = ctx.obj["settings"]
    with Session(engine) as session:
        app = LazyFeedApp(session, settings)
        app.run()


async def _add_feeds(session: Session, settings: Settings, urls: list[str]):
    feed_repository = FeedRepository(session)
    already_saved_urls = [feed.url for feed in feed_repository.get_all()]
    new_urls = [url for url in urls if url not in already_saved_urls]

    if not new_urls:
        console.print("[bold red]ERROR:[/bold red] There are no new urls to check!")
        return
    with console.status(
        "Fetching new feeds... This will only take a moment!",
        spinner="earth",
    ):
        timeout = aiohttp.ClientTimeout(
            total=settings.client.timeout,
            connect=settings.client.connect_timeout,
        )
        headers = settings.client.headers
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as client:
            tasks = [fetch_feed_metadata(client, url) for url in urls]
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
                        f"[bold green]SUCCESS:[/bold green] Added RSS feed for '{feed_in_db.title}' ({feed_in_db.link})"
                    )


@cli.command(
    name="add",
    help="Add one or more RSS feeds.",
)
@click.argument("urls", nargs=-1)
@click.pass_context
def add_feed(ctx, urls) -> None:
    engine = ctx.obj["engine"]
    settings = ctx.obj["settings"]
    with Session(engine) as session:
        asyncio.run(_add_feeds(session, settings, urls))


@cli.command(
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
    help="Remove specified RSS feed.",
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
    settings = ctx.obj["settings"]
    with Session(engine) as session:
        urls = import_opml(input)
        asyncio.run(_add_feeds(session, settings, urls))


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


@cli.command(name="config", help="Open the configuration file.")
def config() -> None:
    user_editor = os.environ.get("EDITOR", None)
    try:
        if user_editor:
            subprocess.run([user_editor, str(config_file_path)], check=True)
        else:
            subprocess.run(["open", str(config_file_path)], check=True)
    except Exception as e:
        console.print(f"[bold red]ERROR:[/] Failed to open the configuration file: {e}")


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
