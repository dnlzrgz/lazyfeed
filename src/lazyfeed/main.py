import asyncio
import sys
from sqlalchemy import select
from sqlalchemy.orm import Session
from lazyfeed.app import LazyFeedApp, http_client_session
from lazyfeed.feeds import fetch_feed
from lazyfeed.models import Feed
from lazyfeed.settings import Settings
from lazyfeed.utils import import_opml, console


async def fetch_new_feeds(
    settings: Settings, session: Session, feeds: set[str]
) -> None:
    async with http_client_session(
        settings.http_client.timeout,
        settings.http_client.connect_timeout,
        settings.http_client.headers,
    ) as client_session:
        tasks = [fetch_feed(client_session, feed) for feed in feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                console.print(f"❌ something went wrong fetching feed: {result}")
                continue

            try:
                session.add(result)
                session.commit()
                console.print(f'✅ added "{result.url}"')
            except Exception as e:
                session.rollback()
                console.print(
                    f"❌ something went wrong while saving feeds to the database: {e}"
                )


def main():
    settings = Settings()
    app = LazyFeedApp(settings)
    session = app.session

    if not sys.stdin.isatty():
        with console.status(
            "[green]importing feeds from file... please, wait a moment",
            spinner="earth",
        ) as status:
            opml_content = sys.stdin.read()
            feeds_in_file = import_opml(opml_content)

            console.print("✅ file read correctly")

            stmt = select(Feed.url)
            results = session.execute(stmt).scalars().all()
            new_feeds = {feed for feed in feeds_in_file if feed not in results}
            if not new_feeds:
                console.print("✅ all feeds had been already added")
                return

            status.update(f"[green]fetching {len(new_feeds)} new feeds...[/]")
            asyncio.run(fetch_new_feeds(settings, session, new_feeds))
            return

    app.run()


if __name__ == "__main__":
    main()
