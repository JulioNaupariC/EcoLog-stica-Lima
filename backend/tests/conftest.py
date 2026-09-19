"""Unit tests never inherit database credentials from the developer."""

import pytest


@pytest.fixture(autouse=True)
def isolated_unit_environment(request, monkeypatch, tmp_path):
    if request.node.get_closest_marker("integration"):
        return
    for name in (
        "DATABASE_URL",
        "APP_ENV",
        "DB_CONNECT_TIMEOUT",
        "SESSION_TTL_MINUTES",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
