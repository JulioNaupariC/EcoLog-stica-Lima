"""Synchronous engine and transaction lifecycle."""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


def build_engine(settings: Settings) -> Engine:
    if settings.database_url is None:
        raise ValueError("DATABASE_URL is required for database operations")
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": settings.db_connect_timeout},
    )


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Caller controls commit; unfinished transactions roll back on close."""
    with factory() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
