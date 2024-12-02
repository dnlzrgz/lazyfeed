from sqlalchemy.orm import Session
import rich_click as click
from lazyfeed.repositories import FeedRepository, PostRepository
from lazyfeed.utils import console, sqids


@click.command(
    name="delete",
    help="Remove specified RSS feed.",
)
@click.argument("feed_id")
@click.pass_context
def delete_feed(ctx, feed_id):
    engine = ctx.obj["engine"]
    with Session(engine) as session:
        feed_repo = FeedRepository(session)
        post_repo = PostRepository(session)

        decoded_id = sqids.decode(feed_id)[0]
        feed = feed_repo.delete(decoded_id)
        if not feed:
            console.print(f"[red]ERR[/] No feed found with ID '{feed_id}'.")
            return

        posts = post_repo.get_by_attributes(feed_id=feed.id)
        for post in posts:
            post_repo.delete(post.id)

        console.print(
            f"[green]OK[/] [link={feed.url}]{feed.title}[/] deleted correctly!"
        )
