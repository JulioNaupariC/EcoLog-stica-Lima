from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_authenticated_session,
    get_authentication_service,
)
from app.api.driver_reports import get_driver_report_service
from app.core.config import Settings
from app.core.rbac import Identidad, Permiso, Rol
from app.main import create_app
from app.schemas.driver_report import (
    AssignedStopResponse,
    DriverReportAcknowledgement,
)
from app.services.autenticacion import AuthenticatedSession
from app.services.autorizacion import AutorizacionService
from app.services.driver_reports import (
    DriverReportAlreadyFinal,
    DriverReportIdentityConflict,
    DriverReportService,
    DriverReportStopNotAssigned,
    DriverReportUnavailable,
)


def client_for(role: Rol = Rol.CONDUCTOR):
    app = create_app(Settings(database_url=None))
    identity = Identidad(uuid4(), role, "ACTIVO")
    service = Mock()
    audit = Mock()
    app.dependency_overrides[get_authenticated_session] = lambda: AuthenticatedSession(
        uuid4(), identity
    )
    app.dependency_overrides[get_driver_report_service] = lambda: service
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(audit)
        yield client, service, audit, identity


def report_payload(**changes):
    payload = {
        "operation_id": str(uuid4()),
        "stop_id": str(uuid4()),
        "status": "ENTREGADO",
    }
    payload.update(changes)
    return payload


def test_conductor_reads_only_authenticated_assignment_summary():
    stop_id = uuid4()
    for client, service, audit, identity in client_for():
        service.list_assignments.return_value = [
            AssignedStopResponse(
                stop_id=stop_id,
                position=2,
                status="PENDIENTE",
            )
        ]

        response = client.get("/conductor/itinerario")

        assert response.status_code == 200
        assert response.json() == {
            "stops": [
                {
                    "stop_id": str(stop_id),
                    "position": 2,
                    "status": "PENDIENTE",
                }
            ]
        }
        service.list_assignments.assert_called_once_with(identity.usuario_id)
        assert (
            audit.registrar.call_args.args[0].detalle.permiso
            is Permiso.ITINERARIOS_CONSULTAR
        )


def test_conductor_report_uses_session_identity_and_returns_acknowledgement():
    payload = report_payload()
    for client, service, audit, identity in client_for():
        service.save_report.return_value = DriverReportAcknowledgement(
            operation_id=payload["operation_id"]
        )

        response = client.post("/conductor/reportes", json=payload)

        assert response.status_code == 200
        assert response.json() == {
            "operation_id": payload["operation_id"],
            "acknowledged": True,
        }
        service.save_report.assert_called_once()
        assert service.save_report.call_args.args[0] == identity.usuario_id
        assert service.save_report.call_args.args[1].model_dump(mode="json") == {
            "operation_id": payload["operation_id"],
            "stop_id": payload["stop_id"],
            "status": "ENTREGADO",
        }
        assert (
            audit.registrar.call_args.args[0].detalle.permiso
            is Permiso.PARADAS_REPORTAR
        )


@pytest.mark.parametrize(
    "role",
    [Rol.ADMINISTRADOR, Rol.OPERADOR, Rol.ANALISTA, Rol.AUDITOR],
)
def test_non_conductor_cannot_read_or_report(role):
    for client, service, _, _ in client_for(role):
        assert client.get("/conductor/itinerario").status_code == 403
        assert (
            client.post("/conductor/reportes", json=report_payload()).status_code == 403
        )
        service.list_assignments.assert_not_called()
        service.save_report.assert_not_called()


def test_report_payload_forbids_client_claimed_owner_and_unknown_fields():
    payload = report_payload(owner_id=str(uuid4()))
    for client, service, _, _ in client_for():
        assert client.post("/conductor/reportes", json=payload).status_code == 422
        service.save_report.assert_not_called()


@pytest.mark.parametrize(
    "error,status_code",
    [
        (DriverReportStopNotAssigned(), 404),
        (DriverReportIdentityConflict(), 409),
        (DriverReportAlreadyFinal(), 409),
        (DriverReportUnavailable("private database details"), 503),
    ],
)
def test_report_errors_are_sanitized(error, status_code):
    for client, service, _, _ in client_for():
        service.save_report.side_effect = error

        response = client.post("/conductor/reportes", json=report_payload())

        assert response.status_code == status_code
        assert "private database details" not in response.text


def test_missing_session_is_401():
    app = create_app(Settings(database_url=None))
    app.dependency_overrides[get_driver_report_service] = lambda: Mock()
    app.dependency_overrides[get_authentication_service] = lambda: Mock()

    with TestClient(app) as client:
        assert client.get("/conductor/itinerario").status_code == 401
        assert (
            client.post("/conductor/reportes", json=report_payload()).status_code == 401
        )


def test_missing_database_factory_is_reported_as_unavailable():
    with pytest.raises(HTTPException) as error:
        get_driver_report_service(Mock(app=Mock(state=Mock(session_factory=None))))

    assert error.value.status_code == 503


def test_report_service_is_constructed_from_the_application_factory():
    factory = Mock()

    service = get_driver_report_service(
        Mock(app=Mock(state=Mock(session_factory=factory)))
    )

    assert isinstance(service, DriverReportService)


def test_itinerary_storage_failure_is_sanitized():
    for client, service, _, _ in client_for():
        service.list_assignments.side_effect = DriverReportUnavailable(
            "private database details"
        )

        response = client.get("/conductor/itinerario")

        assert response.status_code == 503
        assert response.json() == {"detail": "Servicio no disponible"}
        assert "private database details" not in response.text
