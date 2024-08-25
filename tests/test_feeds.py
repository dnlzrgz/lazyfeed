from aiohttp import web
import pytest
from lazyfeed.feeds import fetch_feed_metadata, fetch_feed, fetch_post
from lazyfeed.models import Feed

feed = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
    <channel>
        <title>Example RSS</title>
        <link>https://example.com/</link>
        <description>Latest posts from example's blog</description>
        <atom:link href="https://example.com/rss/" rel="self"/>
        <lastBuildDate>Thu, 15 Aug 2024 19:55:29 +0000</lastBuildDate>
        <item>
            <title>Example post</title>
            <link>https://example.com/blog/post/</link>
            <description><![CDATA[A simple change than can protect you and your site from basic brute force attacks.]]></description>
            <pubDate>Thu, 15 Aug 2024 19:50:00 +0000</pubDate>
            <guid>https://example.com/blog/post/</guid>
        </item>
    </channel>
</rss>
"""

empty_feed = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
    <channel>
        <title>Empty RSS</title>
        <link>https://example.com/</link>
        <description>No posts available.</description>
    </channel>
</rss>
"""

post = """<html>
<head>
<title>Post</title>
</head>
<body>
<h1>Example post</h1>
<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
</body>
</html>
"""


async def rss_success(request):
    return web.Response(status=200, text=feed)


async def rss_bad_format(request):
    return web.Response(status=200, text="\n" + feed)


async def rss_empty(request):
    return web.Response(status=200, text="")


async def rss_not_found(request):
    return web.Response(status=404, text="")


async def rss_not_modified(request):
    return web.Response(status=304, text="")


async def post_success(request):
    return web.Response(status=200, text=post)


async def post_not_found(request):
    return web.Response(status=404, text="")


def create_app():
    app = web.Application()
    app.router.add_get("/rss_success", rss_success)
    app.router.add_get("/rss_bad_format", rss_bad_format)
    app.router.add_get("/rss_empty", rss_empty)
    app.router.add_get("/rss_not_found", rss_not_found)
    app.router.add_get("/rss_not_modified", rss_not_modified)
    app.router.add_get("/post_success", post_success)
    app.router.add_get("/post_not_found", post_not_found)

    return app


async def test_fetch_feed_bad_url(aiohttp_client):
    client = await aiohttp_client(create_app())
    with pytest.raises(RuntimeError):
        await fetch_feed_metadata(client, "/")


async def test_fetch_feed_metadata_success(aiohttp_client):
    client = await aiohttp_client(create_app())
    result = await fetch_feed_metadata(client, "/rss_success")

    assert result is not None
    assert result.title == "Example RSS"
    assert result.link == "https://example.com/"


async def test_fetch_feed_metadata_bad_format(aiohttp_client):
    client = await aiohttp_client(create_app())
    with pytest.raises(RuntimeError):
        await fetch_feed_metadata(client, "/rss_bad_format")


async def test_fetch_feed_metadata_not_found(aiohttp_client):
    client = await aiohttp_client(create_app())
    with pytest.raises(RuntimeError):
        await fetch_feed_metadata(client, "/rss_not_found")


async def test_fetch_feed_success(aiohttp_client):
    feed = Feed(
        url="/rss_success",
        link="https://example.com",
        title="Example",
    )
    client = await aiohttp_client(create_app())
    entries, etag = await fetch_feed(client, feed)
    assert len(entries) == 1
    assert etag == ""


async def test_fetch_feed_success_but_empty(aiohttp_client):
    feed = Feed(
        url="/rss_empty",
        link="https://example.com",
        title="Example",
    )
    client = await aiohttp_client(create_app())
    entries, etag = await fetch_feed(client, feed)
    assert len(entries) == 0
    assert etag == ""


async def test_fetch_feed_not_modified(aiohttp_client):
    feed = Feed(
        url="/rss_not_modified",
        link="https://example.com",
        title="Example",
        etag="12345",
    )

    client = await aiohttp_client(create_app())
    entries, etag = await fetch_feed(client, feed)
    assert len(entries) == 0
    assert etag == "12345"


async def test_fetch_post_bad_url(aiohttp_client):
    client = await aiohttp_client(create_app())
    with pytest.raises(RuntimeError):
        await fetch_post(client, "/")


async def test_fetch_post_success(aiohttp_client):
    client = await aiohttp_client(create_app())
    content = await fetch_post(client, "/post_success")
    assert content is not None


async def test_fetch_post_not_found(aiohttp_client):
    client = await aiohttp_client(create_app())
    with pytest.raises(RuntimeError):
        await fetch_post(client, "/post_not_found")
