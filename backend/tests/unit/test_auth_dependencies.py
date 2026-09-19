from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.dependencies import require_permission
from app.core.rbac import Identidad, Permiso, Rol
from app.services.autenticacion import AuthenticatedSession
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
