import shutil
import click
from importlib.metadata import version
from pathlib import Path
from typing import Type, Tuple
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

APP_NAME = "lazyfeed"
APP_DIR = Path(click.get_app_dir(app_name=APP_NAME))
DB_URL: Path = APP_DIR / f"{APP_NAME}.db"
CONFIG_FILE_PATH = APP_DIR / "config.toml"
TEMPLATE_FILE_PATH = Path(__file__).parent / "config_template.toml"


class ClientSettings(BaseModel):
    timeout: int = 300
    connect_timeout: int = 10
    headers: dict = {}


class Settings(BaseSettings):
    name: str = APP_NAME
    version: str = version(APP_NAME)

    http_client: ClientSettings = Field(default_factory=ClientSettings)

    theme: str = "dracula"

    auto_read: bool = False
    auto_load: bool = False
    confirm_before_read: bool = True
    sort_by: str = "published_at"
    sort_order: str = "ascending"

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        toml_file=f"{APP_DIR / 'config.toml'}",
        validate_default=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        APP_DIR.mkdir(parents=True, exist_ok=True)

        if not CONFIG_FILE_PATH.exists():
            shutil.copy(TEMPLATE_FILE_PATH, CONFIG_FILE_PATH)

        return (
            env_settings,
            TomlConfigSettingsSource(settings_cls),
        )


if __name__ == "__main__":
    settings = Settings()
    print(settings.model_dump())
