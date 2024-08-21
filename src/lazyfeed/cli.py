import click
import httpx
from sqlalchemy import create_engine, exc, text
from sqlalchemy.orm import Session
from lazyfeed.db import init_db
from lazyfeed.errors import BadHTTPRequest, BadRSSFeed
from lazyfeed.feeds import fetch_feed_metadata
from lazyfeed.opml_utils import export_opml, import_opml
from lazyfeed.repositories import FeedRepository
from lazyfeed.tui import LazyFeedApp


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx) -> None:
    ctx.ensure_object(dict)

    engine = create_engine("sqlite:///lazyfeed.db")
    init_db(engine)
    ctx.obj["engine"] = engine

    client = httpx.Client(timeout=10, follow_redirects=True)
    ctx.obj["client"] = client
    if ctx.invoked_subcommand is None:
        ctx.forward(start_tui)


@cli.command(name="tui")
@click.pass_context
def start_tui(ctx) -> None:
    engine = ctx.obj["engine"]
    client = ctx.obj["client"]
    with Session(engine) as session:
        app = LazyFeedApp(session, client)
        app.run()

    client.close()


def _add_feeds(session, client, urls):
    feed_repository = FeedRepository(session)
    for url in urls:
        try:
            feed = fetch_feed_metadata(client, url)
            feeds_in_db = feed_repository.get_by_attributes(url=feed.url)
            if feeds_in_db:
                click.echo(f"Warning: feed '{url}' already added!")
                continue

            feed_repository.add(feed)
            click.echo(f"Success: added feed from '{url}'")
        except BadHTTPRequest as http_exc:
            click.echo(f"Error: while fetching '{url}': {http_exc}.")
        except BadRSSFeed as rss_exc:
            click.echo(f"Error while parsing the feed from '{url}': {rss_exc}.")

    client.close()


@cli.command(name="add")
@click.argument("urls", nargs=-1)
@click.pass_context
def add_feed(ctx, urls) -> None:
    engine = ctx.obj["engine"]
    client = ctx.obj["client"]
    with Session(engine) as session:
        _add_feeds(session, client, urls)


@cli.command(name="import")
@click.argument("input", type=click.File("rb"))
@click.pass_context
def import_feeds(ctx, input) -> None:
    engine = ctx.obj["engine"]
    client = ctx.obj["client"]
    with Session(engine) as session:
        urls = import_opml(input)
        _add_feeds(session, client, urls)


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
