import aiohttp
import feedparser
from lazyfeed.models import Feed


async def fetch_feed(
    client: aiohttp.ClientSession,
    url: str,
    title: str | None = None,
) -> Feed:
    try:
        resp = await client.get(url)
        resp.raise_for_status()
    except aiohttp.ClientError as e:
        raise RuntimeError(f'failed to fetch feed from "{url}": {e}')

    content = await resp.text()
    d = feedparser.parse(content)
    if d.bozo:
        raise RuntimeError(f"feed is badly formatted: {d.bozo_exception}")

    metadata = d["channel"]
    feed = Feed(
        url=url,
        title=title or metadata.get("title"),
        site=metadata.get("link"),
        description=metadata.get("description", ""),
    )

    return feed


async def fetch_feed_entries(
    client: aiohttp.ClientSession,
    url: str,
) -> list[dict]:
    try:
        resp = await client.get(url)
        resp.raise_for_status()
    except aiohttp.ClientError as e:
        raise RuntimeError(f'failed to fetch items from "{url}": {e}')

    content = await resp.text()
    d = feedparser.parse(content)
    if d.bozo:
        raise RuntimeError(f"feed is badly formatted: {d.bozo_exception}")

    return d.get("entries", [])
