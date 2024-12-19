import aiohttp
from contextlib import asynccontextmanager
from lazyfeed.settings import Settings


@asynccontextmanager
async def http_client_session(settings: Settings):
    client_timeout = aiohttp.ClientTimeout(
        total=settings.http_client.timeout,
        connect=settings.http_client.connect_timeout,
    )

    async with aiohttp.ClientSession(
        timeout=client_timeout,
        headers=settings.http_client.headers,
    ) as session:
        yield session
