"""ST-024 regressions for availability boundaries and HTTP rejection contracts."""

from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_conductor_api import client_for
from test_conductor_service import account, driver

from app.api.conductores import get_conductor_service
from app.api.dependencies import get_authentication_service
from app.core.config import Settings
from app.main import create_app
from app.services.conductores import LIMA, ConductorUnavailable, _response


@pytest.mark.parametrize(
    "end_offset,expected",
    [(-1, False), (0, False), (1, True)],
    ids=["availability-ended", "availability-ends-now", "availability-still-valid"],
)
def test_availability_end_is_exclusive(end_offset, expected):
    now = datetime(2026, 10, 9, 12, tzinfo=LIMA)
    row = driver()
    row.licencia_vigente_hasta = now.date()
    row.disponible_desde = now - timedelta(hours=2)
    row.disponible_hasta = now + timedelta(seconds=end_offset)
    with patch("app.services.conductores.datetime") as clock:
        clock.now.return_value = now
        assert _response(row, account(row.usuario_id)).habilitado_asignacion is expected


def test_future_nine_hour_availability_is_not_driving_time():
    now = datetime(2026, 10, 9, 12, tzinfo=LIMA)
    row = driver()
    row.licencia_vigente_hasta = date(2099, 12, 31)
    row.disponible_desde = now + timedelta(days=1)
    row.disponible_hasta = row.disponible_desde + timedelta(hours=9)
    with patch("app.services.conductores.datetime") as clock:
        clock.now.return_value = now
        assert _response(row, account(row.usuario_id)).habilitado_asignacion is True


@pytest.mark.parametrize("method", ["GET-list", "GET-detail", "POST", "PATCH"])
def test_every_driver_operation_requires_a_session(method):
    app = create_app(Settings(database_url=None))
    service = Mock()
    app.dependency_overrides[get_authentication_service] = lambda: Mock()
    app.dependency_overrides[get_conductor_service] = lambda: service
    path = "/conductores"
    if method in {"GET-detail", "PATCH"}:
        path += f"/{uuid4()}"
    with TestClient(app) as client:
        response = client.request(method.split("-")[0], path, json={})
    assert response.status_code == 401
    assert not service.mock_calls


@pytest.mark.parametrize("operation", ["list", "detail", "create", "update"])
def test_unavailable_storage_returns_sanitized_503(operation):
    from test_conductor_schemas import payload

    with client_for() as (client, service, _, _):
        method = {
            "list": "list_page",
            "detail": "get",
            "create": "create",
            "update": "update",
        }[operation]
        getattr(service, method).side_effect = ConductorUnavailable("private SQL")
        if operation == "list":
            response = client.get("/conductores")
        elif operation == "detail":
            response = client.get(f"/conductores/{uuid4()}")
        elif operation == "create":
            response = client.post("/conductores", json=payload())
        else:
            response = client.patch(f"/conductores/{uuid4()}", json={"nombre": "Nuevo"})
        assert response.status_code == 503
        assert response.json() == {"detail": "Servicio no disponible"}


@pytest.mark.parametrize("method", ["GET", "PATCH"])
def test_invalid_uuid_is_rejected_before_storage(method):
    with client_for() as (client, service, _, _):
        response = client.request(
            method, "/conductores/not-a-uuid", json={"nombre": "A"}
        )
        assert response.status_code == 422
        assert not service.mock_calls
