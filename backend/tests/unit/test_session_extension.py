from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import (
    COOKIE_NAME,
    get_authentication_service,
    get_current_session,
)
from app.core.config import Settings
from app.core.rbac import Identidad, Rol
from app.main import create_app
from app.repositories.auditoria import AuditStorageError, Evento
from app.repositories.sesiones import (
    SesionRepository,
    SessionIdentity,
    SessionStorageError,
)
from app.services import autenticacion as module
from app.services.autenticacion import (
    AutenticacionService,
    AuthenticatedSession,
    AuthenticationUnavailable,
    InvalidSession,
    LoginResult,
    SessionExtension,
    SessionLimitReached,
)

NOW = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)


@pytest.fixture
def extension_service(monkeypatch):
    factory = MagicMock()
    repository = Mock()
    audit = Mock()
    monkeypatch.setattr(module, "SesionRepository", Mock(return_value=repository))
    monkeypatch.setattr(module, "AuditoriaRepository", Mock(return_value=audit))
    identity = Identidad(uuid4(), Rol.OPERADOR, "ACTIVO")
    authenticated = AuthenticatedSession(uuid4(), identity)
    found = SessionIdentity(
        authenticated.sesion_id,
        identity.usuario_id,
        identity.rol.value,
        "ACTIVO",
        None,
        NOW + timedelta(minutes=1),
        None,
        creado_en=NOW - timedelta(minutes=59),
    )
    repository.lock_for_extension.return_value = found
    return (
        AutenticacionService(factory, Mock(), ttl_minutes=60),
        repository,
        audit,
        authenticated,
        found,
    )


def test_extension_uses_clock_and_audits_in_business_transaction(extension_service):
    service, repository, audit, authenticated, found = extension_service
    result = service.extend(authenticated, now=NOW)
    assert result.expira_en == NOW + timedelta(minutes=60)
    assert result.max_expira_en == found.creado_en + timedelta(hours=12)
    assert result.max_age == 3600
    repository.extend.assert_called_once_with(found.sesion_id, result.expira_en)
    event = audit.insert.call_args.args[0]
    assert event.evento is Evento.SESION_EXTENDIDA
    assert event.detalle.model_dump(mode="json") == {"resultado": "RENOVACION"}


def test_clipping_then_conflict_before_expiration(extension_service):
    service, repository, _, authenticated, found = extension_service
    created = NOW - timedelta(hours=11, minutes=45)
    repository.lock_for_extension.return_value = replace(found, creado_en=created)
    result = service.extend(authenticated, now=NOW)
    assert result.expira_en == created + timedelta(hours=12)
    assert result.max_age == 900
    repository.lock_for_extension.return_value = replace(
        found, creado_en=created, expira_en=result.expira_en
    )
    with pytest.raises(SessionLimitReached):
        service.extend(authenticated, now=NOW)


@pytest.mark.parametrize(
    "changes",
    [
        {"expira_en": NOW},
        {"revocada_en": NOW},
        {"estado": "INACTIVO"},
        {"bloqueado_hasta": NOW + timedelta(minutes=15)},
        {"rol": "UNKNOWN"},
        {"creado_en": NOW - timedelta(hours=12)},
        {"creado_en": None},
        {"usuario_id": uuid4()},
    ],
)
def test_invalid_session_is_not_extended(extension_service, changes):
    service, repository, audit, authenticated, found = extension_service
    repository.lock_for_extension.return_value = replace(found, **changes)
    with pytest.raises(InvalidSession):
        service.extend(authenticated, now=NOW)
    repository.extend.assert_not_called()
    audit.insert.assert_not_called()


def test_missing_session(extension_service):
    service, repository, _, authenticated, _ = extension_service
    repository.lock_for_extension.return_value = None
    with pytest.raises(InvalidSession):
        service.extend(authenticated, now=NOW)


@pytest.mark.parametrize(
    "error", [SessionStorageError("private"), SQLAlchemyError("private")]
)
def test_storage_errors_are_sanitized(extension_service, error):
    service, repository, _, authenticated, _ = extension_service
    repository.lock_for_extension.side_effect = error
    with pytest.raises(AuthenticationUnavailable, match="^Authentication unavailable$"):
        service.extend(authenticated, now=NOW)


def test_audit_failure_aborts_transaction(extension_service):
    service, _, audit, authenticated, _ = extension_service
    audit.insert.side_effect = AuditStorageError("private")
    with pytest.raises(AuthenticationUnavailable):
        service.extend(authenticated, now=NOW)
    context = service._business_factory.begin.return_value
    assert context.__exit__.call_args.args[0] is AuditStorageError


@pytest.mark.parametrize(
    "environment,secure", [("development", False), ("production", True)]
)
def test_http_extension_keeps_token_and_correct_cookie(environment, secure):
    app = create_app(Settings(app_env=environment, database_url=None))
    service = Mock()
    auth = AuthenticatedSession(uuid4(), Identidad(uuid4(), Rol.OPERADOR, "ACTIVO"))
    service.extend.return_value = SessionExtension(
        NOW + timedelta(minutes=15), NOW + timedelta(minutes=15), 900
    )
    app.dependency_overrides[get_authentication_service] = lambda: service
    app.dependency_overrides[get_current_session] = lambda: auth
    with TestClient(app, base_url="https://testserver") as client:
        client.cookies.set(COOKIE_NAME, "S" * 43)
        response = client.post("/sesion/extender")
    assert response.status_code == 200
    assert response.json() == {
        "expires_at": "2026-11-07T12:15:00Z",
        "max_expires_at": "2026-11-07T12:15:00Z",
    }
    assert response.headers["cache-control"] == "no-store"
    cookie = response.headers["set-cookie"]
    assert "S" * 43 in cookie and "Max-Age=900" in cookie
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/" in cookie
    assert ("Secure" in cookie) is secure
    assert "S" * 43 not in response.text


@pytest.mark.parametrize(
    "error,status",
    [
        (InvalidSession(), 401),
        (SessionLimitReached(), 409),
        (AuthenticationUnavailable(), 503),
    ],
)
def test_http_denials_have_no_new_cookie(error, status):
    app = create_app(Settings(database_url=None))
    service = Mock()
    service.extend.side_effect = error
    app.dependency_overrides[get_authentication_service] = lambda: service
    app.dependency_overrides[get_current_session] = lambda: AuthenticatedSession(
        uuid4(), Identidad(uuid4(), Rol.AUDITOR, "ACTIVO")
    )
    with TestClient(app) as client:
        client.cookies.set(COOKIE_NAME, "S" * 43)
        response = client.post("/sesion/extender")
    assert response.status_code == status
    assert "set-cookie" not in response.headers
    if status == 409:
        assert (
            response.json()["detail"]
            == "La sesión alcanzó su duración máxima; vuelve a iniciar sesión"
        )


@pytest.mark.parametrize("token", ["short", "S" * 44, "S" * 42 + ";"])
def test_extension_rejects_noncanonical_cookie(token):
    app = create_app(Settings(database_url=None))
    service = Mock()
    app.dependency_overrides[get_authentication_service] = lambda: service
    app.dependency_overrides[get_current_session] = lambda: AuthenticatedSession(
        uuid4(), Identidad(uuid4(), Rol.AUDITOR, "ACTIVO")
    )
    with TestClient(app) as client:
        client.cookies.set(COOKIE_NAME, token)
        response = client.post("/sesion/extender")
    assert response.status_code == 401
    assert "set-cookie" not in response.headers
    service.extend.assert_not_called()


def test_no_cookie_and_untrusted_origin():
    app = create_app(Settings(database_url=None))
    service = Mock()
    app.dependency_overrides[get_authentication_service] = lambda: service
    with TestClient(app) as client:
        assert client.post("/sesion/extender").status_code == 401
    app.dependency_overrides[get_current_session] = lambda: AuthenticatedSession(
        uuid4(), Identidad(uuid4(), Rol.AUDITOR, "ACTIVO")
    )
    with TestClient(app) as client:
        assert (
            client.post(
                "/sesion/extender", headers={"Origin": "https://foreign.example"}
            ).status_code
            == 403
        )
    service.extend.assert_not_called()


@pytest.mark.parametrize("role", list(Rol))
def test_every_role_gets_both_login_deadlines(role):
    app = create_app(Settings(database_url=None))
    service = Mock()
    service.login.return_value = LoginResult(
        "synthetic",
        uuid4(),
        Identidad(uuid4(), role, "ACTIVO"),
        NOW + timedelta(hours=1),
        max_expira_en=NOW + timedelta(hours=12),
    )
    app.dependency_overrides[get_authentication_service] = lambda: service
    with TestClient(app) as client:
        response = client.post(
            "/login", json={"email": "demo@example.test", "password": "synthetic"}
        )
    assert response.json()["expires_at"] == "2026-11-07T13:00:00Z"
    assert response.json()["max_expires_at"] == "2026-11-08T00:00:00Z"


def test_repository_locks_user_then_session_and_copies_creation_time():
    from sqlalchemy.dialects import postgresql

    session = Mock()
    user_id, session_id = uuid4(), uuid4()
    user = SimpleNamespace(
        usuario_id=user_id,
        rol="OPERADOR",
        estado="ACTIVO",
        bloqueado_hasta=None,
        debe_cambiar_contrasena=False,
    )
    row = SimpleNamespace(
        sesion_id=session_id,
        expira_en=NOW + timedelta(hours=1),
        revocada_en=None,
        creado_en=NOW,
    )
    session.scalar.side_effect = [user, row]
    result = SesionRepository(session).lock_for_extension(session_id)
    assert result.creado_en == NOW
    statements = [
        str(call.args[0].compile(dialect=postgresql.dialect()))
        for call in session.scalar.call_args_list
    ]
    assert statements[0].endswith("FOR UPDATE OF usuario")
    assert statements[1].endswith("FOR UPDATE")
    SesionRepository(session).extend(session_id, NOW + timedelta(hours=2))
    session.execute.assert_called_once()


@pytest.mark.parametrize("values", [[None], [Mock(), None]])
def test_repository_missing_rows(values):
    session = Mock()
    session.scalar.side_effect = values
    assert SesionRepository(session).lock_for_extension(uuid4()) is None


def test_repository_errors_are_sanitized():
    session = Mock()
    session.scalar.side_effect = SQLAlchemyError("private")
    session.execute.side_effect = SQLAlchemyError("private")
    with pytest.raises(SessionStorageError, match="^Session storage unavailable$"):
        SesionRepository(session).lock_for_extension(uuid4())
    with pytest.raises(SessionStorageError, match="^Session storage unavailable$"):
        SesionRepository(session).extend(uuid4(), NOW)
