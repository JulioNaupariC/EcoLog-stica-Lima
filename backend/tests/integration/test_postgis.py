import pytest

from app.core.config import Settings
from app.db.check import check_database
from app.db.session import build_engine

pytestmark = pytest.mark.integration


def test_real_postgresql_postgis():
    settings = Settings()
    if settings.database_url is None:
        pytest.skip("DATABASE_URL not configured: real validation pending")
    engine = build_engine(settings)
    try:
        check_database(engine)
    finally:
        engine.dispose()
