import os
import subprocess
import rich_click as click
from lazyfeed.utils import console
from lazyfeed.settings import CONFIG_FILE_PATH


@click.command(
    name="config",
    help="Opens the configuration file.",
)
def config() -> None:
    user_editor = os.environ.get("EDITOR", None)
    try:
        if user_editor:
            subprocess.run([user_editor, str(CONFIG_FILE_PATH)], check=True)
        else:
            subprocess.run(["open", str(CONFIG_FILE_PATH)], check=True)
    except Exception as e:
        console.print(f"[red]ERR[/] failed to open the configuration file: {e}")
