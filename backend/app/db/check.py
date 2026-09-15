"""Read-only PostgreSQL 16/PostGIS verification: python -m app.db.check."""

from sqlalchemy import Engine, text

from app.core.config import Settings
from app.db.session import build_engine


def check_database(engine: Engine) -> None:
    with engine.connect() as connection:
        if connection.scalar(text("SELECT 1")) != 1:
            raise RuntimeError("Database probe failed")
        version = int(connection.scalar(text("SHOW server_version_num")))
        if version // 10000 != 16:
            raise RuntimeError("PostgreSQL 16 is required")
        if not connection.scalar(text("SELECT PostGIS_Version()")):
            raise RuntimeError("PostGIS is unavailable")
        srid = connection.scalar(
            text("SELECT ST_SRID(ST_SetSRID(ST_MakePoint(-77.03, -12.04), 4326))")
        )
        if srid != 4326:
            raise RuntimeError("Spatial probe failed")


def main() -> int:
    engine = None
    try:
        engine = build_engine(Settings())
        check_database(engine)
    except Exception:
        print("Database check failed. Check configuration, access and PostGIS.")
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    print("PostgreSQL 16/PostGIS check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
