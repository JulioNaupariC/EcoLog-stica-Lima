"""Migrations use the same external configuration as the application."""

from alembic import context
from app.core.config import Settings
from app.db.base import Base
from app.db.session import build_engine
from app.models import Usuario  # noqa: F401

settings = Settings()
if settings.database_url is None:
    raise RuntimeError("DATABASE_URL is required for migrations")


def include_object(obj, name, type_, reflected, compare_to):
    """PostGIS owns spatial_ref_sys; application migrations must not remove it."""
    return not (
        type_ == "table"
        and name == "spatial_ref_sys"
        and reflected
        and compare_to is None
    )


if context.is_offline_mode():
    context.configure(
        url=settings.database_url.get_secret_value(),
        target_metadata=Base.metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = build_engine(settings)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=Base.metadata,
                include_object=include_object,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
