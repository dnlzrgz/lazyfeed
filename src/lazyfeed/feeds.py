from http import HTTPStatus
from urllib.parse import urlparse
import feedparser
import httpx
from lazyfeed.errors import BadHTTPRequest, BadRSSFeed, BadURL
from lazyfeed.models import Feed


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        raise BadURL(f"URL '{url}' is not valid!")


def fetch_feed_metadata(client: httpx.Client, feed_url: str) -> Feed:
    is_valid_url(feed_url)

    try:
        resp = client.get(feed_url)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise BadHTTPRequest(f"An error occurred while requesting {exc.request.url!r}.")

    d = feedparser.parse(resp.content)
    if d.bozo:
        raise BadRSSFeed(f"An error occured while parsing '{feed_url}'.")

    feed = Feed(
        url=feed_url,
        link=d["channel"]["link"],
        title=d["channel"]["title"],
        description=d["channel"]["description"],
    )

    return feed


def fetch_feed(
    client: httpx.Client, feed_url: str, etag: str | None = None
) -> tuple[list[str], str]:
    try:
        headers = {"ETag": etag} if etag else {}
        resp = client.get(feed_url, headers=headers)

        if resp.status_code == HTTPStatus.NOT_MODIFIED:
            return ([], etag)

        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise BadHTTPRequest(f"An error occurred while requesting {exc.request.url!r}.")

    d = feedparser.parse(resp.content)
    if d.bozo:
        raise BadRSSFeed(f"An error occured while parsing '{feed_url}'.")

    new_etag = resp.headers.get("ETag", "")
    return (d.entries, new_etag)


def fetch_post(client: httpx.Client, post_url: str) -> str:
    try:
        resp = client.get(post_url)
        resp.raise_for_status()
        # TODO: handle timeouts
    except httpx.HTTPError as exc:
        raise BadHTTPRequest(f"An error occurred while requesting {exc.request.url!r}.")

    return resp.text
