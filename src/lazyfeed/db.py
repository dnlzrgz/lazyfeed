from lazyfeed.models import Base


def init_db(engine) -> None:
    """
    Initialize database by creating all tables defined in the
    ORM models.
    """

    Base.metadata.create_all(engine)
