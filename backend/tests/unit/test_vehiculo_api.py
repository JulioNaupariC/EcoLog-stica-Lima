from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.dependencies import get_authenticated_session, get_authentication_service
from app.api.vehiculos import get_vehicle_service
from app.core.config import Settings
from app.core.rbac import Identidad, Rol
from app.main import create_app
from app.models.vehiculo import Vehiculo
from app.services.autenticacion import AuthenticatedSession
from app.services.autorizacion import AutorizacionService
from app.services.vehiculos import (
    VehicleDuplicatePlate,
    VehicleInactive,
    VehicleNotFound,
    VehicleUnavailable,
)


def vehicle():
    return Vehiculo(
        vehiculo_id=uuid4(),
        placa="ABC123",
        tipo="CAMIONETA",
        capacidad_kg=Decimal("1000.00"),
        capacidad_m3=Decimal("8.00"),
        rendimiento_km_l=Decimal("10.000"),
        factor_co2_kg_km=Decimal("0.30000"),
        anio_fabricacion=2024,
        estado="ACTIVO",
    )


def client_for(role=Rol.ADMINISTRADOR):
    app = create_app(Settings(database_url=None))
    identity = Identidad(uuid4(), role, "ACTIVO")
    authenticated = AuthenticatedSession(uuid4(), identity)
    service = Mock()
    app.dependency_overrides[get_authenticated_session] = lambda: authenticated
    app.dependency_overrides[get_vehicle_service] = lambda: service
    audit = Mock()
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(audit)
        yield client, service


def payload():
    return {
        "placa": " abc123 ",
        "tipo": "CAMIONETA",
        "capacidad_kg": "1000.00",
        "capacidad_m3": "8.00",
        "rendimiento_km_l": "10.000",
        "factor_co2_kg_km": "0.30000",
        "anio_fabricacion": 2024,
    }


def test_admin_http_contracts_and_normalization():
    for client, service in client_for():
        row = vehicle()
        service.create.return_value = row
        service.list_all.return_value = [row]
        service.get.return_value = row
        service.update.return_value = row
        assert client.post("/vehiculos", json=payload()).status_code == 201
        assert service.create.call_args.args[0].placa == "ABC123"
        assert client.get("/vehiculos").status_code == 200
        assert client.get(f"/vehiculos/{row.vehiculo_id}").status_code == 200
        assert (
            client.patch(
                f"/vehiculos/{row.vehiculo_id}", json={"rendimiento_km_l": "11"}
            ).status_code
            == 200
        )
        assert client.delete(f"/vehiculos/{row.vehiculo_id}").status_code == 204


@pytest.mark.parametrize(
    "error,status_code",
    [
        (VehicleNotFound(), 404),
        (VehicleDuplicatePlate(), 409),
        (VehicleInactive(), 409),
        (VehicleUnavailable("private SQL"), 503),
    ],
)
def test_http_errors_are_sanitized(error, status_code):
    for client, service in client_for():
        service.update.side_effect = error
        response = client.patch(f"/vehiculos/{uuid4()}", json={"placa": "ABC123"})
        assert response.status_code == status_code
        assert "private SQL" not in response.text


@pytest.mark.parametrize(
    "role,method,expected",
    [
        (Rol.OPERADOR, "post", 201),
        (Rol.OPERADOR, "delete", 403),
        (Rol.AUDITOR, "get", 200),
        (Rol.AUDITOR, "post", 403),
        (Rol.CONDUCTOR, "get", 403),
        (Rol.ANALISTA, "get", 403),
    ],
)
def test_vehicle_rbac(role, method, expected):
    for client, service in client_for(role):
        row = vehicle()
        service.create.return_value = row
        service.list_all.return_value = [row]
        if method == "post":
            response = client.post("/vehiculos", json=payload())
        elif method == "delete":
            response = client.delete(f"/vehiculos/{row.vehiculo_id}")
        else:
            response = client.get("/vehiculos")
        assert response.status_code == expected


def test_missing_session_is_401():
    app = create_app(Settings(database_url=None))
    app.dependency_overrides[get_vehicle_service] = lambda: Mock()
    app.dependency_overrides[get_authentication_service] = lambda: Mock()
    with TestClient(app) as client:
        assert client.get("/vehiculos").status_code == 401


def test_vehicle_service_dependency_is_unavailable_without_database():
    app = create_app(Settings(database_url=None))
    with TestClient(app) as client:
        with pytest.raises(HTTPException) as error:
            get_vehicle_service(Mock(app=client.app))
    assert error.value.status_code == 503
