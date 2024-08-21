from http import HTTPStatus
from typing import Any
import httpx
import feedparser
from lazyfeed.errors import BadHTTPRequest, BadRSSFeed
from lazyfeed.models import Feed


def fetch_feed_metadata(client: httpx.Client, feed_url: str) -> Feed:
    try:
        resp = client.get(feed_url)
        resp.raise_for_status()
    except httpx.ConnectTimeout:
        raise BadHTTPRequest(
            f"Failed to fetch feed from '{feed_url}'. Connection timeout."
        )
    except httpx.HTTPError as exc:
        raise BadHTTPRequest(
            f"Failed to fetch feed from '{feed_url}'. HTTP status code: {exc.response.status_code}."
        )
    except Exception as exc:
        raise BadHTTPRequest(f"Failed to fetch feed from '{feed_url}': {exc}.")

    d = feedparser.parse(resp.content)
    if d.bozo:
        raise BadRSSFeed(f"Failed to parse RSS feed from '{feed_url}'.")

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
    except httpx.HTTPError as exc:
        raise BadHTTPRequest(
            f"Failed to fetch feed from '{feed_url}'. HTTP status code: {exc.response.status_code}."
        )

    d = feedparser.parse(resp.content)
    if d.bozo:
        raise BadRSSFeed(f"Failed to parse RSS feed from '{feed_url}'.")

    new_etag = resp.headers.get("ETag", "")
    return d.entries, new_etag


def fetch_post(client: httpx.Client, post_url: str) -> str:
    try:
        resp = client.get(post_url)
        resp.raise_for_status()
    except httpx.ConnectTimeout:
        raise BadHTTPRequest(
            f"Failed to fetch content from post '{post_url}'. Connection timeout."
        )
    except httpx.HTTPError as exc:
        raise BadHTTPRequest(
            f"Failed to fetch post from '{post_url}'. HTTP status code: {exc.response.status_code}."
        )
    except Exception as exc:
        raise BadHTTPRequest(f"Failed to fetch post from '{post_url}': {exc}.")

    return resp.text
