import rich_click as click
from sqlalchemy.orm import Session
from sqlalchemy import exc, text
from lazyfeed.utils import console


@click.command(
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
            console.print("[green]OK[/] unused space reclaimed!")
        except exc.SQLAlchemyError as e:
            console.print(f"[red]ERR[/] something went wrong: {e}!")
