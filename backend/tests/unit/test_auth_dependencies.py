from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.dependencies import get_authenticated_session, require_permission
from app.core.rbac import Contexto, Identidad, Permiso, Rol
from app.repositories.auditoria import AuditStorageError
from app.services.autenticacion import (
    AuthenticatedSession,
    AuthenticationUnavailable,
    InvalidSession,
)
from app.services.autorizacion import AuthorizationDenied


def test_permission_dependency_uses_database_resolved_identity():
    authorization = Mock()
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(authorization_service=authorization))
    )
    authenticated = AuthenticatedSession(
        uuid4(), Identidad(uuid4(), Rol.OPERADOR, "ACTIVO")
    )
    dependency = require_permission(Permiso.PEDIDOS_CREAR)
    assert dependency(request, authenticated) == authenticated.identidad
    authorization.autorizar.assert_called_once_with(
        authenticated.identidad, Permiso.PEDIDOS_CREAR
    )


def test_permission_dependency_can_supply_a_self_ownership_context():
    authorization = Mock()
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(authorization_service=authorization))
    )
    authenticated = AuthenticatedSession(
        uuid4(), Identidad(uuid4(), Rol.CONDUCTOR, "ACTIVO")
    )
    dependency = require_permission(
        Permiso.ITINERARIOS_CONSULTAR,
        lambda identity: Contexto(propietario_id=identity.usuario_id),
    )

    assert dependency(request, authenticated) == authenticated.identidad
    authorization.autorizar.assert_called_once_with(
        authenticated.identidad,
        Permiso.ITINERARIOS_CONSULTAR,
        Contexto(propietario_id=authenticated.identidad.usuario_id),
    )


def test_permission_dependency_returns_generic_forbidden():
    authorization = Mock()
    authorization.autorizar.side_effect = AuthorizationDenied("private")
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(authorization_service=authorization))
    )
    authenticated = AuthenticatedSession(
        uuid4(), Identidad(uuid4(), Rol.AUDITOR, "ACTIVO")
    )
    with pytest.raises(HTTPException) as error:
        require_permission(Permiso.PEDIDOS_CREAR)(request, authenticated)
    assert error.value.status_code == 403
    assert error.value.detail == "Acceso denegado"


def test_missing_authorization_service_fails_closed():
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    authenticated = AuthenticatedSession(
        uuid4(), Identidad(uuid4(), Rol.ADMINISTRADOR, "ACTIVO")
    )

    with pytest.raises(HTTPException) as error:
        require_permission(Permiso.VEHICULOS_CREAR)(request, authenticated)

    assert error.value.status_code == 503
    assert error.value.detail == "Servicio no disponible"


def test_audit_storage_failure_never_grants_http_access():
    authorization = Mock()
    authorization.autorizar.side_effect = AuditStorageError("private SQL details")
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(authorization_service=authorization))
    )
    authenticated = AuthenticatedSession(
        uuid4(), Identidad(uuid4(), Rol.ADMINISTRADOR, "ACTIVO")
    )

    with pytest.raises(HTTPException) as error:
        require_permission(Permiso.VEHICULOS_CREAR)(request, authenticated)

    assert error.value.status_code == 503
    assert error.value.detail == "Servicio no disponible"
    assert "SQL" not in error.value.detail


@pytest.mark.parametrize(
    "failure,expected_status",
    [
        (InvalidSession("private session state"), 401),
        (AuthenticationUnavailable("private database details"), 503),
    ],
)
def test_session_resolution_failures_are_sanitized(failure, expected_status):
    service = Mock()
    service.resolve.side_effect = failure
    request = SimpleNamespace(
        cookies={"ecologistica_session": "opaque-token"},
        app=SimpleNamespace(state=SimpleNamespace()),
    )

    with pytest.raises(HTTPException) as error:
        get_authenticated_session(request, service)

    assert error.value.status_code == expected_status
    assert error.value.detail in {"No autenticado", "Servicio no disponible"}
    assert "private" not in error.value.detail


def test_absent_cookie_does_not_resolve_a_session():
    service = Mock()
    request = SimpleNamespace(cookies={}, app=SimpleNamespace(state=SimpleNamespace()))

    with pytest.raises(HTTPException) as error:
        get_authenticated_session(request, service)

    assert error.value.status_code == 401
    assert error.value.detail == "No autenticado"
    service.resolve.assert_not_called()
