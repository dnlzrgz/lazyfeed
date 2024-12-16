from datetime import datetime
import aiohttp
import feedparser
from selectolax.parser import HTMLParser
from markdownify import markdownify as md
from lazyfeed.models import Feed, Item


def clean_html(html: str) -> str | None:
    tree = HTMLParser(html)
    tags = ["canvas", "footer", "head", "header", "iframe", "nav", "script", "style"]
    tree.strip_tags(tags)
    return tree.html


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


async def fetch_entries(
    client: aiohttp.ClientSession,
    url: str,
    etag: str = "",
) -> tuple[list[dict], str]:
    headers = {}
    if etag:
        headers["If-None-Match"] = etag

    try:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
    except aiohttp.ClientError as e:
        raise RuntimeError(f'failed to fetch items from "{url}": {e}')

    if resp.status == 304:
        return [], etag

    content = await resp.text()
    d = feedparser.parse(content)
    if d.bozo:
        raise RuntimeError(f"feed is badly formatted: {d.bozo_exception}")

    return d.get("entries", []), resp.headers.get("Etag", "")


async def fetch_content(
    client: aiohttp.ClientSession, entry_data: dict, feed_id: int
) -> Item | None:
    url = entry_data.get("link")
    title = entry_data.get("title", "")
    author = entry_data.get("author", "")
    description = entry_data.get("description", "")
    published_parsed = entry_data.get("published_parsed")

    assert url

    try:
        resp = await client.get(url)
        resp.raise_for_status()
    except aiohttp.ClientError as e:
        raise RuntimeError(f'failed to fetch contents from "{url}": {e}')

    raw_content = await resp.text()
    md_content = md(clean_html(raw_content))

    published_at = None
    if published_parsed:
        published_at = datetime(*published_parsed[:6])

    return Item(
        title=title,
        url=url,
        author=author,
        description=description,
        raw_content=raw_content,
        content=md_content,
        feed_id=feed_id,
        published_at=published_at,
    )
