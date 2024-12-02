import asyncio
from sqlalchemy.orm import Session
import aiohttp
import rich_click as click
from lazyfeed.settings import Settings
from lazyfeed.feeds import fetch_feed_metadata
from lazyfeed.models import Feed
from lazyfeed.repositories import FeedRepository
from lazyfeed.utils import console


async def _add_feeds(session: Session, settings: Settings, urls: list[str]):
    feed_repository = FeedRepository(session)
    already_saved_urls = [feed.url for feed in feed_repository.get_all()]
    new_urls = [url for url in urls if url not in already_saved_urls]

    if not new_urls:
        console.print("[red]ERR[/] There are no new urls to check!")
        return
    with console.status(
        "Fetching new feeds... This will only take a moment!",
        spinner="earth",
    ):
        timeout = aiohttp.ClientTimeout(
            total=settings.client.timeout,
            connect=settings.client.connect_timeout,
        )
        headers = settings.client.headers
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as client:
            tasks = [fetch_feed_metadata(client, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for url, result in zip(urls, results):
                if isinstance(result, Exception):
                    console.print(f"[red]ERR[/] [link={url}]{url}[/]")
                else:
                    assert isinstance(result, Feed)

                    feed_in_db = feed_repository.add(result)
                    console.print(
                        f"[green]OK[/] [link={feed_in_db.link}]{feed_in_db.title}[/]"
                    )


@click.command(
    name="add",
    help="Add one or more RSS feeds.",
)
@click.argument("urls", nargs=-1)
@click.pass_context
def add_feed(ctx, urls) -> None:
    engine = ctx.obj["engine"]
    settings = ctx.obj["settings"]
    with Session(engine) as session:
        asyncio.run(_add_feeds(session, settings, urls))
