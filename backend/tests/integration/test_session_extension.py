from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text

from alembic import command
from app.api.dependencies import COOKIE_NAME, get_authentication_service
from app.core.config import Settings
from app.core.rbac import Rol
from app.db.session import session_factory
from app.main import create_app
from app.models import Auditoria, Sesion
from app.repositories.auditoria import AuditoriaRepository, AuditStorageError
from app.repositories.sesiones import SesionRepository
from app.repositories.usuarios import UsuarioRepository
from app.services.auditoria import AuditoriaService
from app.services.autenticacion import (
    AutenticacionService,
    AuthenticationUnavailable,
    InvalidSession,
)
from app.services.credenciales import CredentialService

pytestmark = pytest.mark.integration
NOW = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)


@pytest.fixture
def extension_database(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    with factory.begin() as session:
        CredentialService(UsuarioRepository(session)).create(
            "session@example.test", "synthetic", "OPERADOR"
        )
    service = AutenticacionService(factory, AuditoriaService(factory), ttl_minutes=60)
    try:
        yield factory, service, config, engine
    finally:
        with factory.begin() as session:
            session.execute(
                delete(Auditoria).where(
                    Auditoria.accion.in_(
                        ("LOGIN_EXITOSO", "SESION_EXTENDIDA", "SESION_CERRADA")
                    )
                )
            )


def test_real_http_cookie_ten_extensions_clipping_limit_and_expiration(
    extension_database,
):
    factory, service, _, _ = extension_database
    clock = {"now": NOW}

    class ClockService:
        def login(self, email, password):
            return service.login(email, password, now=clock["now"])

        def resolve(self, token):
            return service.resolve(token, now=clock["now"])

        def extend(self, authenticated):
            return service.extend(authenticated, now=clock["now"])

    app = create_app(Settings(database_url=None))
    app.dependency_overrides[get_authentication_service] = ClockService
    with TestClient(app) as client:
        response = client.post(
            "/login", json={"email": "session@example.test", "password": "synthetic"}
        )
        assert response.status_code == 200
        assert response.json()["max_expires_at"] == "2026-11-08T00:00:00Z"
        assert "Max-Age=43200" in response.headers["set-cookie"]
        token = client.cookies.get(COOKIE_NAME)
        for index in range(1, 13):
            clock["now"] = NOW + timedelta(minutes=58 * index)
            response = client.post("/sesion/extender")
            assert response.status_code == 200
            assert "set-cookie" not in response.headers
            assert client.cookies.get(COOKIE_NAME) == token
        assert response.json()["expires_at"] == "2026-11-08T00:00:00Z"
        assert client.post("/sesion/extender").status_code == 409
        clock["now"] = NOW + timedelta(hours=12)
        assert client.post("/sesion/extender").status_code == 401
    with factory() as session:
        events = session.scalars(
            select(Auditoria).where(Auditoria.accion == "SESION_EXTENDIDA")
        ).all()
        assert len(events) == 12
        assert all(
            row.entidad == "sesion" and row.detalle == {"resultado": "RENOVACION"}
            for row in events
        )
        assert token not in str([row.detalle for row in events])
        assert session.scalar(select(Sesion)).creado_en == NOW


def test_audit_failure_rolls_back_expiration_and_keeps_hash(
    extension_database, monkeypatch
):
    factory, service, _, _ = extension_database
    result = service.login("session@example.test", "synthetic", now=NOW)
    auth = service.resolve(result.token, now=NOW)
    with factory() as session:
        original_hash = session.get(Sesion, result.sesion_id).token_hash

    def fail(self, registro):
        raise AuditStorageError("synthetic failure")

    monkeypatch.setattr(AuditoriaRepository, "insert", fail)
    with pytest.raises(AuthenticationUnavailable):
        service.extend(auth, now=NOW + timedelta(minutes=30))
    with factory() as session:
        row = session.get(Sesion, result.sesion_id)
        assert row.expira_en == result.expira_en
        assert row.token_hash == original_hash


def test_revocation_between_authentication_and_extension(extension_database):
    factory, service, _, _ = extension_database
    result = service.login("session@example.test", "synthetic", now=NOW)
    auth = service.resolve(result.token, now=NOW)
    with factory.begin() as session:
        SesionRepository(session).revoke(result.sesion_id, NOW)
    with pytest.raises(InvalidSession):
        service.extend(auth, now=NOW)


@pytest.mark.parametrize("role", list(Rol))
def test_every_role_can_extend_without_changing_token(extension_database, role):
    factory, service, _, _ = extension_database
    with factory.begin() as session:
        CredentialService(UsuarioRepository(session)).create(
            "role@example.test", "synthetic", role.value
        )
    login = service.login("role@example.test", "synthetic", now=NOW)
    extended = service.extend(
        service.resolve(login.token, now=NOW), now=NOW + timedelta(minutes=30)
    )
    assert extended.expira_en == NOW + timedelta(minutes=90)
    assert (
        service.resolve(login.token, now=NOW + timedelta(minutes=89)).identidad.rol
        is role
    )


def test_migration_round_trip_removes_only_extension_events(extension_database):
    factory, service, config, engine = extension_database
    login = service.login("session@example.test", "synthetic", now=NOW)
    service.extend(
        service.resolve(login.token, now=NOW), now=NOW + timedelta(minutes=30)
    )
    command.downgrade(config, "-1")
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM auditoria WHERE accion='SESION_EXTENDIDA'")
            )
            == 0
        )
        assert (
            connection.scalar(
                text("SELECT count(*) FROM auditoria WHERE accion='LOGIN_EXITOSO'")
            )
            == 1
        )
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "0014_resolver_incidencias"
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "0015_sesion_extendida"
        )
