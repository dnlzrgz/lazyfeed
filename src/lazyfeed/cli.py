from sqlalchemy import create_engine
import rich_click as click
from lazyfeed.settings import Settings
from lazyfeed.commands import (
    add_feed,
    delete_feed,
    export_feeds,
    import_feeds,
    list_feeds,
    config,
    start_tui,
    vacuum,
)
from lazyfeed.db import init_db

settings = Settings()
engine = create_engine(f"sqlite:///{settings.db_url}")
init_db(engine)


@click.group(
    help=settings.description,
    epilog="Check out https://github.com/dnlzrgz/lazyfeed for more details",
    context_settings=dict(
        help_option_names=["-h", "--help"],
    ),
)
@click.version_option(version=settings.version)
@click.pass_context
def cli(ctx) -> None:
    ctx.ensure_object(dict)
    ctx.obj["settings"] = settings
    ctx.obj["engine"] = engine


cli.add_command(add_feed)
cli.add_command(delete_feed)
cli.add_command(export_feeds)
cli.add_command(import_feeds)
cli.add_command(list_feeds)
cli.add_command(config)
cli.add_command(start_tui)
cli.add_command(vacuum)
