from typing import Type, Tuple
from pathlib import Path
import shutil
import click
from textual.design import ColorSystem
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

app_dir = Path(click.get_app_dir(app_name="lazyfeed"))
config_file_path = app_dir / "config.toml"
template_file_path = Path(__file__).parent / "config_template.toml"


class ClientSettings(BaseModel):
    timeout: int = 300
    connect_timeout: int = 10
    headers: dict = {}


class Theme(BaseModel):
    primary: str | None = Field(default="#7dc4e4")
    secondary: str | None = Field(default="#cad3f5")
    background: str | None = Field(default="#24273a")
    surface: str | None = Field(default="#5b6078")
    success: str | None = Field(default="#a6da95")
    warning: str | None = Field(default="#f5a97f")
    error: str | None = Field(default="#ed8796")
    dark: bool = True

    def to_color_system(self) -> ColorSystem:
        """
        Convert current theme to a ColorSystem.
        """

        return ColorSystem(**self.model_dump())


class AppSettings(BaseModel):
    db_url: str = f"sqlite:///{app_dir / 'lazyfeed.db'}"

    theme: Theme = Field(default_factory=Theme)

    auto_mark_as_read: bool = False
    ask_before_marking_as_read: bool = False
    show_read: bool = False
    sort_by: str = "title"
    sort_order: str = "descending"


class Settings(BaseSettings):
    client: ClientSettings = Field(default_factory=ClientSettings)
    app: AppSettings = Field(default_factory=AppSettings)

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        toml_file=f"{app_dir / 'config.toml'}",
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
        app_dir.mkdir(parents=True, exist_ok=True)

        if not config_file_path.exists():
            shutil.copy(template_file_path, config_file_path)

        return (
            env_settings,
            TomlConfigSettingsSource(settings_cls),
        )


if __name__ == "__main__":
    settings = Settings()
    print(settings.model_dump())

    print(settings.app.theme.to_color_system().generate())
