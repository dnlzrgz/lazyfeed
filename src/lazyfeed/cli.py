import click
import httpx
from sqlalchemy import create_engine, exc, text
from sqlalchemy.orm import Session
from lazyfeed.db import init_db
from lazyfeed.errors import BadHTTPRequest, BadRSSFeed, BadURL
from lazyfeed.feeds import fetch_feed_metadata
from lazyfeed.opml_utils import export_opml, import_opml
from lazyfeed.repositories import FeedRepository
from lazyfeed.tui import LazyFeedApp

client = httpx.Client(follow_redirects=True)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx) -> None:
    ctx.ensure_object(dict)

    # TODO: check later
    engine = create_engine("sqlite:///lazyfeed.db")
    init_db(engine)

    ctx.obj["engine"] = engine
    if ctx.invoked_subcommand is None:
        ctx.forward(start_tui)


@cli.command(name="tui")
@click.pass_context
def start_tui(ctx) -> None:
    engine = ctx.obj["engine"]
    with Session(engine) as session:
        app = LazyFeedApp(session)
        app.run()


def _add_feeds(session, urls):
    feed_repository = FeedRepository(session)
    for url in urls:
        try:
            feed = fetch_feed_metadata(client, url)
            feed_repository.add(feed)
            click.echo(f"Success: added feed from '{url}'")
        except BadURL:
            click.echo(f"Error: '{url}' is invalid.")
            continue
        except BadHTTPRequest as http_exc:
            click.echo(f"Error: while fetching '{url}': {http_exc}.")
            continue
        except BadRSSFeed as rss_exc:
            click.echo(f"Error while parsing the feed from '{url}': {rss_exc}.")
            continue
        except exc.IntegrityError:
            pass


@cli.command(name="add")
@click.argument("urls", nargs=-1)
@click.pass_context
def add_feed(ctx, urls) -> None:
    engine = ctx.obj["engine"]
    with Session(engine) as session:
        _add_feeds(session, urls)


@cli.command(name="import")
@click.argument("input", type=click.File("rb"))
@click.pass_context
def import_feeds(ctx, input) -> None:
    engine = ctx.obj["engine"]
    with Session(engine) as session:
        urls = import_opml(input)
        _add_feeds(session, urls)


@cli.command(name="export")
@click.argument("output", type=click.File("wb"), default="lazyfeed.opml")
@click.pass_context
def export_feeds(ctx, output) -> None:
    engine = ctx.obj["engine"]
    with Session(engine) as session:
        feed_repository = FeedRepository(session)
        feeds = feed_repository.get_all()

        if not len(feeds):
            click.echo("Error: No feeds found to export.")
            return

        export_opml(feeds, output)


@cli.command(name="vacuum")
@click.pass_context
def vacuum(ctx) -> None:
    engine = ctx.obj["engine"]
    with Session(engine) as session:
        try:
            session.execute(text("VACUUM"))
            session.commit()
            click.echo("Success: unused space has been reclaimed.")
        except exc.SQLAlchemyError as e:
            click.echo(f"Error: while vacuum operation {e}")
