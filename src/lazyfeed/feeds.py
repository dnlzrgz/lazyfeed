from http import HTTPStatus
import logging
from typing import Any
import httpx
import feedparser
from lazyfeed.models import Feed


def fetch_feed_metadata(client: httpx.Client, feed_url: str) -> Feed:
    try:
        resp = client.get(feed_url)
        resp.raise_for_status()
    except (httpx.ConnectTimeout, httpx.HTTPError, Exception) as err:
        logging.error(f"Failed to fetch feed from {feed_url}: {err}")
        raise

    d = feedparser.parse(resp.content)
    if d.bozo:
        logging.error(f"Failed to parse feed from {feed_url}")
        raise

    metadata = d["channel"]
    feed = Feed(
        url=feed_url,
        link=metadata.get("link"),
        title=metadata.get("title"),
        description=metadata.get("description", ""),
    )

    return feed


def fetch_feed(
    client: httpx.Client, feed_url: str, etag: str | None = None
) -> tuple[list[Any], str]:
    try:
        headers = {"ETag": etag} if etag else {}
        resp = client.get(feed_url, headers=headers)

        if resp.status_code == HTTPStatus.NOT_MODIFIED:
            return [], etag or ""

        resp.raise_for_status()
    except (httpx.ConnectTimeout, httpx.HTTPError, Exception) as err:
        logging.error(f"Failed to fetch feed from {feed_url}: {err}")
        raise

    d = feedparser.parse(resp.content)
    if d.bozo:
        logging.error(f"Failed to parse feed from {feed_url}")
        raise

    new_etag = resp.headers.get("ETag", "")
    return d.entries, new_etag


def fetch_post(client: httpx.Client, post_url: str) -> str:
    try:
        resp = client.get(post_url)
        resp.raise_for_status()
    except (httpx.ConnectTimeout, httpx.HTTPError, Exception) as err:
        logging.error(f"Failed to fetch contetn from {post_url}: {err}")
        raise

    return resp.text
