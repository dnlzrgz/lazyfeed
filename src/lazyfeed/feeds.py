from http import HTTPStatus
from typing import Any
import httpx
import feedparser
from lazyfeed.models import Feed


async def fetch_feed_metadata(client: httpx.AsyncClient, feed_url: str) -> Feed:
    try:
        resp = await client.get(feed_url)
        resp.raise_for_status()
    except (httpx.ConnectTimeout, httpx.HTTPError, Exception):
        raise

    d = feedparser.parse(resp.content)
    if d.bozo:
        raise

    metadata = d["channel"]
    feed = Feed(
        url=feed_url,
        link=metadata.get("link"),
        title=metadata.get("title"),
        description=metadata.get("description", ""),
    )

    return feed


async def fetch_feed(client: httpx.AsyncClient, feed: Feed) -> tuple[list[Any], str]:
    try:
        headers = {"ETag": feed.etag} if feed.etag else {}
        resp = await client.get(feed.url, headers=headers)

        if resp.status_code == HTTPStatus.NOT_MODIFIED:
            return [], feed.etag

        resp.raise_for_status()
    except (httpx.ConnectTimeout, httpx.HTTPError, Exception):
        raise

    d = feedparser.parse(resp.content)
    if d.bozo:
        raise

    new_etag = resp.headers.get("ETag", "")
    return d.entries, new_etag


async def fetch_post(client: httpx.AsyncClient, post_url: str) -> str:
    try:
        resp = await client.get(post_url)
        resp.raise_for_status()
    except (httpx.ConnectTimeout, httpx.HTTPError, Exception):
        raise

    return resp.text
