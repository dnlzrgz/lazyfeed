import aiohttp
from contextlib import asynccontextmanager
from lazyfeed.settings import Settings


@asynccontextmanager
async def http_client_session(settings: Settings):
    """
    Asynchronous context manager for creating an HTTP client session using
    aiohttp.ClientSession. It configures the session with specified timeouts
    and headers from the provided settings, and the session is automatically
    closed upon exiting the context.
    """

    client_timeout = aiohttp.ClientTimeout(
        total=settings.http_client.timeout,
        connect=settings.http_client.connect_timeout,
    )

    async with aiohttp.ClientSession(
        timeout=client_timeout,
        headers=settings.http_client.headers,
    ) as session:
        yield session
