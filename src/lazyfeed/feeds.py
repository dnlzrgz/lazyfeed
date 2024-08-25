from typing import Any
import aiohttp
import feedparser
from lazyfeed.models import Feed


async def fetch_feed_metadata(client: aiohttp.ClientSession, feed_url: str) -> Feed:
    resp = await client.get(feed_url)

    if resp.status >= 400:
        raise RuntimeError(f"Bad status code {resp.status}")

    content = await resp.text()
    d = feedparser.parse(content)
    if d.bozo:
        raise RuntimeError("Feed is bad formatted")

    metadata = d["channel"]
    feed = Feed(
        url=feed_url,
        link=metadata.get("link"),
        title=metadata.get("title"),
        description=metadata.get("description", ""),
    )

    return feed


async def fetch_feed(
    client: aiohttp.ClientSession, feed: Feed
) -> tuple[list[Any], str]:
    headers = {"ETag": feed.etag} if feed.etag else {}
    resp = await client.get(feed.url, headers=headers)

    if resp.status == 304:
        return [], feed.etag

    if resp.status >= 400:
        raise RuntimeError(f"Bad status code {resp.status}")

    content = await resp.text()
    d = feedparser.parse(content)
    if d.bozo:
        raise RuntimeError("Feed is bad formatted")

    new_etag = resp.headers.get("ETag", "")
    return d.entries, new_etag


async def fetch_post(client: aiohttp.ClientSession, post_url: str) -> str:
    resp = await client.get(post_url)
    if resp.status >= 400:
        raise RuntimeError(f"Bad status code {resp.status}")

    return await resp.text()
