from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ClientSettings(BaseModel):
    max_keepalive_connections: int = 5
    max_connections: int = 10
    timeout: int = 5
    follow_redirects: bool = True


class AppSettings(BaseModel):
    show_Read: bool = False
    mark_as_read_on_open: bool = True


class Settings(BaseSettings):
    client: ClientSettings = Field(default_factory=ClientSettings)
    app: AppSettings = Field(default_factory=AppSettings)


if __name__ == "__main__":
    print(Settings().model_dump())
