"""Read-only readiness probe with its own bounded connection pool."""

from time import perf_counter

from sqlalchemy import Engine, create_engine, text

from app.core.config import Settings
from app.monitoring.metrics import Metrics


def build_probe_engine(settings: Settings) -> Engine | None:
    if settings.database_url is None:
        return None
    return create_engine(
        settings.database_url.get_secret_value(),
        hide_parameters=True,
        pool_size=1,
        max_overflow=0,
        pool_timeout=0.2,
        pool_pre_ping=False,
        connect_args={"connect_timeout": 2, "options": "-c statement_timeout=2000"},
    )


def probe_database(engine: Engine | None, metrics: Metrics) -> tuple[bool, float]:
    started = perf_counter()
    available = False
    try:
        if engine is not None:
            with engine.connect() as connection:
                available = connection.scalar(text("SELECT 1")) == 1
    except Exception:
        # Do not leak URLs, drivers, SQL, parameters or credentials in the response.
        available = False
    elapsed = perf_counter() - started
    available = available and elapsed <= 5.0
    metrics.database_probe(available, elapsed)
    return available, elapsed
