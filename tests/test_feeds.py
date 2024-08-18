from http import HTTPStatus
import pytest
import httpx
from lazyfeed.errors import BadHTTPRequest, BadRSSFeed
from lazyfeed.feeds import fetch_feed_metadata, fetch_feed, fetch_post

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


def mock_response(request):
    if request.url.path == "/rss/success":
        return httpx.Response(HTTPStatus.OK, content=feed)
    if request.url.path == "/rss/bad-format":
        return httpx.Response(HTTPStatus.OK, content="\n" + feed)
    if request.url.path == "/rss/empty":
        return httpx.Response(HTTPStatus.OK, content=empty_feed)
    if request.url.path == "/rss/not-modified":
        return httpx.Response(HTTPStatus.NOT_MODIFIED, content="")
    if request.url.path == "/blog/post/":
        return httpx.Response(HTTPStatus.OK, content=post)
    else:
        return httpx.Response(HTTPStatus.NOT_FOUND, content="")


test_client = httpx.Client(transport=httpx.MockTransport(mock_response))


def test_fetch_feed_metadata_success():
    feed_url = "https://example.com/rss/success"
    result = fetch_feed_metadata(test_client, feed_url)

    assert result is not None
    assert result.url == feed_url
    assert result.title == "Example RSS"
    assert result.link == "https://example.com/"


def test_fetch_feed_metadata_bad_format():
    feed_url = "https://example.com/rss/bad-format"
    with pytest.raises(BadRSSFeed):
        fetch_feed_metadata(test_client, feed_url)


def test_fetch_feed_metadata_not_found():
    feed_url = "https://example.com/rss/not-found"
    with pytest.raises(BadHTTPRequest):
        fetch_feed_metadata(test_client, feed_url)


def test_fetch_feed_success():
    feed_url = "https://example.com/rss/success"
    entries, etag = fetch_feed(test_client, feed_url)
    assert len(entries) == 1
    assert etag == ""


def test_fetch_feed_success_but_empty():
    feed_url = "https://example.com/rss/empty"
    entries, etag = fetch_feed(test_client, feed_url)
    assert len(entries) == 0
    assert etag == ""


def test_fetch_feed_not_modified():
    feed_url = "https://example.com/rss/not-modified"
    entries, etag = fetch_feed(test_client, feed_url, "12345")
    assert len(entries) == 0
    assert etag == "12345"


def test_fetch_post_success():
    post_url = "https://example.com/blog/post/"
    content = fetch_post(test_client, post_url)
    assert content is not None


def test_fetch_post_not_found():
    post_url = "https://example.com/blog/missing"
    with pytest.raises(BadHTTPRequest):
        fetch_post(test_client, post_url)
