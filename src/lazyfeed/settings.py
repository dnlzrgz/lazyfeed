from typing import Type, Tuple
from pathlib import Path
import click
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

_app_dir = Path(click.get_app_dir(app_name="lazyfeed"))


class ClientSettings(BaseModel):
    timeout: int = 300
    connect_timeout: int | None = None
    headers: dict = {}


class AppSettings(BaseModel):
    sqlite_url: str = f"sqlite:///{_app_dir / 'lazyfeed.db'}"


class Settings(BaseSettings):
    client: ClientSettings = Field(default_factory=ClientSettings)
    app: AppSettings = Field(default_factory=AppSettings)

    model_config = SettingsConfigDict(toml_file=f"{_app_dir / 'config.toml'}")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        _app_dir.mkdir(parents=True, exist_ok=True)
        return (TomlConfigSettingsSource(settings_cls),)
