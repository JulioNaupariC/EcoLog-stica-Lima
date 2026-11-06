from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_authenticated_session, get_authentication_service
from app.api.pedidos import get_pedido_service
from app.core.config import Settings
from app.core.rbac import Identidad, Permiso, Rol
from app.main import create_app
from app.schemas.pedido import PedidoResponse
from app.services.autenticacion import AuthenticatedSession
from app.services.autorizacion import AutorizacionService
from app.services.pedidos import PedidoClienteNoEncontrado, PedidoUnavailable


def request_payload(**changes):
    data = {
        "cliente_id": str(uuid4()),
        "direccion": "Av. Principal 123",
        "referencia": "Frente al parque",
        "latitud": -11.9,
        "longitud": -76.9,
        "peso_kg": "12.50",
        "volumen_m3": "0.080",
        "ventana_inicio": "2026-10-01T09:00:00-05:00",
        "ventana_fin": "2026-10-01T11:00:00-05:00",
        "prioridad": "ESTANDAR",
        "tipo_producto": "Libre",
    }
    data.update(changes)
    return data


def response_for(data):
    return PedidoResponse(
        pedido_id=uuid4(),
        cliente_id=data["cliente_id"],
        direccion=data["direccion"],
        referencia=data["referencia"],
        latitud=data["latitud"],
        longitud=data["longitud"],
        peso_kg=Decimal(data["peso_kg"]),
        volumen_m3=Decimal(data["volumen_m3"]),
        ventana_inicio=data["ventana_inicio"],
        ventana_fin=data["ventana_fin"],
        prioridad=data["prioridad"],
        tipo_producto=data["tipo_producto"],
        estado="PENDIENTE",
    )


def client_for(role):
    app = create_app(Settings(database_url=None))
    identity = Identidad(uuid4(), role, "ACTIVO")
    app.dependency_overrides[get_authenticated_session] = lambda: AuthenticatedSession(
        uuid4(), identity
    )
    service = Mock()
    app.dependency_overrides[get_pedido_service] = lambda: service
    audit = Mock()
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(audit)
        yield client, service, audit


@pytest.mark.parametrize("role", [Rol.OPERADOR, Rol.ADMINISTRADOR])
def test_authorized_creation_201_and_exact_permission(role):
    for client, service, audit in client_for(role):
        data = request_payload()
        service.create.return_value = response_for(data)
        response = client.post("/pedidos", json=data)
        assert response.status_code == 201
        assert response.json()["estado"] == "PENDIENTE"
        assert response.json()["peso_kg"] == "12.50"
        assert str(service.create.call_args.args[0].cliente_id) == data["cliente_id"]
        assert (
            audit.registrar.call_args.args[0].detalle.permiso is Permiso.PEDIDOS_CREAR
        )


@pytest.mark.parametrize("role", [Rol.AUDITOR, Rol.CONDUCTOR, Rol.ANALISTA])
def test_role_without_create_permission_is_denied(role):
    for client, service, _ in client_for(role):
        assert client.post("/pedidos", json=request_payload()).status_code == 403
        service.create.assert_not_called()


@pytest.mark.parametrize(
    "error,status_code",
    [(PedidoClienteNoEncontrado(), 404), (PedidoUnavailable("private SQL"), 503)],
)
def test_errors_are_sanitized(error, status_code):
    for client, service, _ in client_for(Rol.OPERADOR):
        service.create.side_effect = error
        response = client.post("/pedidos", json=request_payload())
        assert response.status_code == status_code
        assert "private SQL" not in response.text


def test_invalid_request_returns_422():
    for client, service, _ in client_for(Rol.OPERADOR):
        response = client.post(
            "/pedidos", json=request_payload(ventana_fin="2026-10-01T08:00:00-05:00")
        )
        assert response.status_code == 422
        # ECL-84: sanitized like the rest of the API, still pointing at the
        # field so the form can show it, and never echoing the value sent.
        assert response.json() == {
            "detail": [
                {
                    "loc": ["body", "ventana_fin"],
                    "type": "value_error",
                    "msg": "Entrada inválida",
                }
            ]
        }
        service.create.assert_not_called()


def test_missing_session_is_401():
    app = create_app(Settings(database_url=None))
    app.dependency_overrides[get_pedido_service] = lambda: Mock()
    app.dependency_overrides[get_authentication_service] = lambda: Mock()
    with TestClient(app) as client:
        assert client.post("/pedidos", json=request_payload()).status_code == 401
