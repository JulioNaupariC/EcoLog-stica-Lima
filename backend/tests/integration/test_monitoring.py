"""Read-only instrumentation checks against the explicitly isolated PostGIS DB."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.config import Settings
from app.main import create_app

pytestmark = pytest.mark.integration


def test_real_database_readiness_and_sql_metrics(migration_database):
    engine, _ = migration_database
    config = Settings(database_url=engine.url.render_as_string(hide_password=False))
    with TestClient(create_app(config)) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["database"] == "up"
        assert response.json()["database_latency_seconds"] <= 5
        with client.app.state.engine.connect() as connection:
            assert connection.scalar(select(1)) == 1
            with pytest.raises(DBAPIError):
                connection.execute(text("SELECT * FROM ecl60_nonexistent_table"))
        output = client.app.state.metrics.render()
        assert 'engine="business",operation="SELECT",outcome="success"} 1' in output
        assert 'engine="business",operation="OTHER",outcome="error"} 1' in output
        assert "ecolog_database_up 1" in output
        assert "ecl60_nonexistent_table" not in output
