from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ClientSettings(BaseModel):
    raise_for_status: bool = False
    timeout: int = 300
    auto_decompress: bool = True


class AppSettings(BaseModel):
    show_Read: bool = False
    mark_as_read_on_open: bool = True


class Settings(BaseSettings):
    client: ClientSettings = Field(default_factory=ClientSettings)
    app: AppSettings = Field(default_factory=AppSettings)
