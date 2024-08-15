import click
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from lazyfeed.db import init_db
from lazyfeed.tui import LazyFeedApp


@click.command()
def run() -> None:
    """
    Starts the lazyfeed TUI.
    """

    # TODO: check later
    engine = create_engine("sqlite:///layfeed.db")
    init_db(engine)

    with Session(engine) as session:
        app = LazyFeedApp(session)
        app.run()
