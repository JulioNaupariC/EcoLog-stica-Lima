"""ECL-32 real HTTP security tests over PostgreSQL.

These tests deliberately keep the production dependency chain intact: login,
opaque cookie, persisted session and user, RBAC, vehicle endpoint and audit.
RNF-004 remains partial because no current HTTP resource exposes DNI/contact data.
"""

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from alembic import command
from app.api.dependencies import COOKIE_NAME
from app.core.config import Settings
from app.core.session_tokens import hash_session_token
from app.db.session import session_factory
from app.main import create_app
from app.models import Auditoria, Sesion, Usuario, Vehiculo
from app.repositories.auditoria import AuditStorageError, Evento
from app.repositories.sesiones import SesionRepository, SessionStorageError
from app.repositories.usuarios import UsuarioRepository
from app.services.credenciales import CredentialService

pytestmark = pytest.mark.integration


@pytest.fixture
def security_database(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    try:
        yield factory, config.attributes["database_url"]
    finally:
        # All evidence belongs to this disposable, validated *_test database.
        # Removing it lets protected migration downgrades cleanly restore base.
        with factory.begin() as session:
            session.execute(delete(Auditoria))


def create_user(factory, email, role, password="correct-password"):
    with factory.begin() as session:
        return CredentialService(UsuarioRepository(session)).create(
            email, password, role
        )


def seed_vehicle(factory, plate="SEC-001"):
    with factory.begin() as session:
        vehicle = Vehiculo(
            placa=plate,
            tipo="CAMIONETA",
            capacidad_kg=Decimal("1000.00"),
            capacidad_m3=Decimal("8.00"),
            rendimiento_km_l=Decimal("10.000"),
            factor_co2_kg_km=Decimal("0.30000"),
            anio_fabricacion=2024,
        )
        session.add(vehicle)
        session.flush()
        return vehicle.vehiculo_id


def vehicle_payload(plate="SEC-NEW"):
    return {
        "placa": plate,
        "tipo": "CAMIONETA",
        "capacidad_kg": "1000.00",
        "capacidad_m3": "8.00",
        "rendimiento_km_l": "10.000",
        "factor_co2_kg_km": "0.30000",
        "anio_fabricacion": 2024,
    }


def login(client, email, password="correct-password"):
    response = client.post("/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response


def security_app(database_url):
    return create_app(Settings(app_env="test", database_url=database_url))


def authorization_rows(session, event=None):
    statement = select(Auditoria).where(
        Auditoria.accion.in_((Evento.PERMITIDA.value, Evento.DENEGADA.value))
    )
    if event is not None:
        statement = statement.where(Auditoria.accion == event.value)
    return list(session.scalars(statement.order_by(Auditoria.creado_en)))


def test_us001_scenario_1_valid_access_and_login_audit(security_database):
    factory, database_url = security_database
    identity = create_user(factory, "admin-security@example.test", "ADMINISTRADOR")
    app = security_app(database_url)

    with TestClient(app) as client:
        login_response = login(client, "admin-security@example.test")
        token = client.cookies.get(COOKIE_NAME)
        assert token
        assert token not in login_response.text
        assert login_response.json() == {
            "usuario_id": str(identity.usuario_id),
            "rol": "ADMINISTRADOR",
            "debe_cambiar_contrasena": False,
        }
        cookie = login_response.headers["set-cookie"]
        assert "HttpOnly" in cookie
        assert "SameSite=strict" in cookie
        assert "Path=/" in cookie
        assert "Max-Age=" in cookie
        assert "Secure" not in cookie

        created = client.post("/vehiculos", json=vehicle_payload("ADM-001"))
        assert created.status_code == 201
        vehicle = created.json()
        vehicle_id = vehicle["vehiculo_id"]
        assert set(vehicle) == {
            "vehiculo_id",
            "placa",
            "tipo",
            "capacidad_kg",
            "capacidad_m3",
            "rendimiento_km_l",
            "factor_co2_kg_km",
            "anio_fabricacion",
            "estado",
        }

        collection = client.get("/vehiculos")
        detail = client.get(f"/vehiculos/{vehicle_id}")
        updated = client.patch(
            f"/vehiculos/{vehicle_id}", json={"rendimiento_km_l": "11.000"}
        )
        deactivated = client.delete(f"/vehiculos/{vehicle_id}")

        assert collection.status_code == 200
        assert detail.status_code == 200
        assert updated.status_code == 200
        assert updated.json()["rendimiento_km_l"] == "11.000"
        assert deactivated.status_code == 204

    with factory() as session:
        stored_session = session.scalar(
            select(Sesion).where(Sesion.token_hash == hash_session_token(token))
        )
        assert stored_session is not None
        assert stored_session.token_hash != token
        successful_logins = list(
            session.scalars(
                select(Auditoria).where(Auditoria.accion == Evento.LOGIN_EXITOSO.value)
            )
        )
        assert len(successful_logins) == 1
        successful_login = successful_logins[0]
        assert successful_login.usuario_id == identity.usuario_id
        assert successful_login.entidad == "sesion"
        assert successful_login.entidad_id == stored_session.sesion_id
        assert successful_login.detalle == {"resultado": "EXITOSO"}
        stored_vehicle = session.get(Vehiculo, vehicle_id)
        assert stored_vehicle.estado == "INACTIVO"

        allowed = authorization_rows(session, Evento.PERMITIDA)
        assert Counter(row.detalle["permiso"] for row in allowed) == Counter(
            {
                "vehiculos.crear": 1,
                "vehiculos.consultar": 2,
                "vehiculos.actualizar": 1,
                "vehiculos.desactivar": 1,
            }
        )
        assert all(row.usuario_id == identity.usuario_id for row in allowed)
        assert all(row.entidad == "vehiculos" for row in allowed)
        assert all(row.entidad_id is None for row in allowed)
        assert all(row.detalle["motivo"] == "PERMITIDO" for row in allowed)

        functional = list(
            session.scalars(select(Auditoria).where(Auditoria.entidad_id == vehicle_id))
        )
        assert {row.accion for row in functional} == {
            Evento.VEHICULO_PARAMETROS_ACTUALIZADOS.value,
            Evento.VEHICULO_DESACTIVADO.value,
        }
        serialized = json.dumps(
            [
                {
                    "entidad": row.entidad,
                    "entidad_id": str(row.entidad_id) if row.entidad_id else None,
                    "detalle": row.detalle,
                }
                for row in allowed
            ]
        )
        for secret in (
            "admin-security@example.test",
            "correct-password",
            token,
            "password_hash",
            "cookie",
            "Traceback",
            "SELECT ",
        ):
            assert secret not in serialized


def test_operator_denied_delete_preserves_active_vehicle(security_database):
    factory, database_url = security_database
    identity = create_user(factory, "operator-security@example.test", "OPERADOR")
    app = security_app(database_url)

    with TestClient(app) as client:
        login(client, "operator-security@example.test")
        created = client.post("/vehiculos", json=vehicle_payload("OPE-001"))
        assert created.status_code == 201
        vehicle_id = created.json()["vehiculo_id"]
        assert client.get("/vehiculos").status_code == 200
        assert client.get(f"/vehiculos/{vehicle_id}").status_code == 200
        patched = client.patch(
            f"/vehiculos/{vehicle_id}", json={"capacidad_kg": "1200.00"}
        )
        assert patched.status_code == 200

        denied = client.delete(f"/vehiculos/{vehicle_id}")
        assert denied.status_code == 403
        assert denied.json() == {"detail": "Acceso denegado"}

    with factory() as session:
        vehicle = session.get(Vehiculo, vehicle_id)
        assert vehicle.estado == "ACTIVO"
        assert vehicle.capacidad_kg == Decimal("1200.00")
        assert (
            session.scalar(
                select(func.count())
                .select_from(Auditoria)
                .where(
                    Auditoria.entidad_id == vehicle_id,
                    Auditoria.accion == Evento.VEHICULO_DESACTIVADO.value,
                )
            )
            == 0
        )
        denied_rows = authorization_rows(session, Evento.DENEGADA)
        assert len(denied_rows) == 1
        denial = denied_rows[0]
        assert denial.usuario_id == identity.usuario_id
        assert denial.entidad == "vehiculos"
        assert denial.entidad_id is None
        assert denial.detalle == {
            "permiso": "vehiculos.desactivar",
            "motivo": "SIN_PERMISO",
        }


def test_us001_scenario_3_role_restriction_preserves_protected_data(
    security_database,
):
    factory, database_url = security_database
    identity = create_user(factory, "auditor-security@example.test", "AUDITOR")
    vehicle_id = seed_vehicle(factory, "AUD-001")
    app = security_app(database_url)

    with factory() as session:
        vehicle = session.get(Vehiculo, vehicle_id)
        before = (
            vehicle.vehiculo_id,
            vehicle.placa,
            vehicle.capacidad_kg,
            vehicle.estado,
        )

    with TestClient(app) as client:
        login(client, "auditor-security@example.test")
        assert client.get("/vehiculos").status_code == 200
        assert client.get(f"/vehiculos/{vehicle_id}").status_code == 200
        responses = (
            client.post("/vehiculos", json=vehicle_payload("AUD-NEW")),
            client.patch(f"/vehiculos/{vehicle_id}", json={"capacidad_kg": "1.00"}),
            client.delete(f"/vehiculos/{vehicle_id}"),
        )
        assert [response.status_code for response in responses] == [403, 403, 403]
        assert all(
            response.json() == {"detail": "Acceso denegado"} for response in responses
        )

    with factory() as session:
        vehicle = session.get(Vehiculo, vehicle_id)
        after = (
            vehicle.vehiculo_id,
            vehicle.placa,
            vehicle.capacidad_kg,
            vehicle.estado,
        )
        assert after == before
        assert vehicle.estado == "ACTIVO"
        assert vehicle.capacidad_kg == Decimal("1000.00")
        assert session.scalar(select(func.count()).select_from(Vehiculo)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(Auditoria)
                .where(
                    Auditoria.entidad_id == vehicle_id,
                    Auditoria.accion == Evento.VEHICULO_PARAMETROS_ACTUALIZADOS.value,
                )
            )
            == 0
        )
        denied = authorization_rows(session, Evento.DENEGADA)
        assert Counter(row.detalle["permiso"] for row in denied) == Counter(
            {
                "vehiculos.crear": 1,
                "vehiculos.actualizar": 1,
                "vehiculos.desactivar": 1,
            }
        )
        assert all(row.usuario_id == identity.usuario_id for row in denied)
        assert all(row.detalle["motivo"] == "SIN_PERMISO" for row in denied)


@pytest.mark.parametrize("role", ["CONDUCTOR", "ANALISTA"])
def test_contextual_roles_cannot_use_general_vehicle_crud(security_database, role):
    factory, database_url = security_database
    identity = create_user(factory, f"{role.lower()}@example.test", role)
    vehicle_id = seed_vehicle(factory, f"{role[:3]}-001")
    app = security_app(database_url)

    with TestClient(app) as client:
        login(client, f"{role.lower()}@example.test")
        responses = (
            client.get("/vehiculos"),
            client.get(f"/vehiculos/{vehicle_id}"),
            client.post("/vehiculos", json=vehicle_payload(f"{role[:3]}-NEW")),
            client.patch(f"/vehiculos/{vehicle_id}", json={"capacidad_kg": "1.00"}),
            client.delete(f"/vehiculos/{vehicle_id}"),
        )
        assert all(response.status_code == 403 for response in responses)
        assert all(
            response.json() == {"detail": "Acceso denegado"} for response in responses
        )

    with factory() as session:
        vehicle = session.get(Vehiculo, vehicle_id)
        assert vehicle.estado == "ACTIVO"
        assert vehicle.capacidad_kg == Decimal("1000.00")
        assert session.scalar(select(func.count()).select_from(Vehiculo)) == 1
        denied = authorization_rows(session, Evento.DENEGADA)
        assert len(denied) == 5
        read_denials = [
            row for row in denied if row.detalle["permiso"] == "vehiculos.consultar"
        ]
        assert len(read_denials) == 2
        assert all(
            row.detalle["motivo"] == "CONTEXTO_INSUFICIENTE" for row in read_denials
        )
        assert all(row.usuario_id == identity.usuario_id for row in denied)
        assert all(row.entidad_id is None for row in denied)


def test_missing_unknown_revoked_and_expired_sessions_never_create(security_database):
    factory, database_url = security_database
    create_user(factory, "session-security@example.test", "ADMINISTRADOR")
    app = security_app(database_url)
    expected = {"detail": "No autenticado"}

    with TestClient(app) as client:
        without_cookie = client.post("/vehiculos", json=vehicle_payload("NO-COOKIE"))
        assert without_cookie.status_code == 401
        assert without_cookie.json() == expected

        client.cookies.set(COOKIE_NAME, "unknown-session-token")
        unknown = client.post("/vehiculos", json=vehicle_payload("UNKNOWN"))
        assert unknown.status_code == 401
        assert unknown.json() == expected

    with TestClient(app) as revoked_client:
        login(revoked_client, "session-security@example.test")
        revoked_token = revoked_client.cookies.get(COOKIE_NAME)
        with factory.begin() as session:
            stored = session.scalar(
                select(Sesion).where(
                    Sesion.token_hash == hash_session_token(revoked_token)
                )
            )
            stored.revocada_en = datetime.now(timezone.utc)
        revoked = revoked_client.post("/vehiculos", json=vehicle_payload("REVOKED"))
        assert revoked.status_code == 401
        assert revoked.json() == expected

    with TestClient(app) as expired_client:
        login(expired_client, "session-security@example.test")
        expired_token = expired_client.cookies.get(COOKIE_NAME)
        with factory.begin() as session:
            stored = session.scalar(
                select(Sesion).where(
                    Sesion.token_hash == hash_session_token(expired_token)
                )
            )
            stored.expira_en = stored.creado_en + timedelta(microseconds=1)
        expired = expired_client.post("/vehiculos", json=vehicle_payload("EXPIRED"))
        assert expired.status_code == 401
        assert expired.json() == expected

    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Vehiculo)) == 0
        assert authorization_rows(session) == []


def test_current_user_state_invalidates_existing_session_without_reactivation(
    security_database,
):
    factory, database_url = security_database
    cases = (
        ("inactive-security@example.test", "INACTIVO", None),
        ("blocked-security@example.test", "BLOQUEADO", None),
        (
            "temporary-security@example.test",
            "ACTIVO",
            datetime.now(timezone.utc) + timedelta(minutes=10),
        ),
    )
    identities = [create_user(factory, email, "ADMINISTRADOR") for email, _, _ in cases]
    app = security_app(database_url)

    with TestClient(app) as client:
        tokens = {}
        for email, _, _ in cases:
            login(client, email)
            tokens[email] = client.cookies.get(COOKIE_NAME)

        with factory.begin() as session:
            for identity, (_, state, blocked_until) in zip(identities, cases):
                user = session.get(Usuario, identity.usuario_id)
                user.estado = state
                user.bloqueado_hasta = blocked_until

        for email, _, _ in cases:
            client.cookies.clear()
            client.cookies.set(COOKIE_NAME, tokens[email])
            response = client.get("/vehiculos")
            assert response.status_code == 401
            assert response.json() == {"detail": "No autenticado"}

    with factory() as session:
        for identity, (_, state, blocked_until) in zip(identities, cases):
            user = session.get(Usuario, identity.usuario_id)
            assert user.estado == state
            assert user.bloqueado_hasta == blocked_until
        assert authorization_rows(session) == []


def test_us001_scenario_2_invalid_credentials_are_indistinguishable(
    security_database,
):
    factory, database_url = security_database
    create_user(factory, "wrong-password@example.test", "OPERADOR")
    inactive = create_user(factory, "inactive-login@example.test", "OPERADOR")
    blocked = create_user(factory, "blocked-login@example.test", "OPERADOR")
    temporary = create_user(factory, "temporary-login@example.test", "OPERADOR")
    blocked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
    with factory.begin() as session:
        session.get(Usuario, inactive.usuario_id).estado = "INACTIVO"
        session.get(Usuario, blocked.usuario_id).estado = "BLOQUEADO"
        session.get(Usuario, temporary.usuario_id).bloqueado_hasta = blocked_until

    attempts = (
        ("wrong-password@example.test", "wrong"),
        ("missing-login@example.test", "correct-password"),
        ("inactive-login@example.test", "correct-password"),
        ("blocked-login@example.test", "correct-password"),
        ("temporary-login@example.test", "correct-password"),
    )
    app = security_app(database_url)
    with TestClient(app) as client:
        responses = [
            client.post("/login", json={"email": email, "password": password})
            for email, password in attempts
        ]

    assert {response.status_code for response in responses} == {401}
    response_bodies = [response.json() for response in responses]
    assert len({json.dumps(body, sort_keys=True) for body in response_bodies}) == 1
    assert all(body == {"detail": "Credenciales inválidas"} for body in response_bodies)
    assert all("set-cookie" not in response.headers for response in responses)
    combined = "".join(response.text for response in responses).lower()
    for private in (
        "missing-login",
        "inactivo",
        "bloqueado",
        "password_hash",
        "sql",
        "traceback",
    ):
        assert private not in combined

    with factory() as session:
        assert session.get(Usuario, inactive.usuario_id).estado == "INACTIVO"
        assert session.get(Usuario, blocked.usuario_id).estado == "BLOQUEADO"
        assert (
            session.get(Usuario, temporary.usuario_id).bloqueado_hasta == blocked_until
        )
        failed = list(
            session.scalars(
                select(Auditoria).where(Auditoria.accion == Evento.LOGIN_FALLIDO.value)
            )
        )
        assert len(failed) == len(attempts)
        assert all(row.usuario_id is None for row in failed)
        details = json.dumps([row.detalle for row in failed])
        assert all(email not in details for email, _ in attempts)


def test_logout_revokes_only_current_real_session(security_database):
    factory, database_url = security_database
    create_user(factory, "multi-session@example.test", "ADMINISTRADOR")
    app = security_app(database_url)

    with TestClient(app) as first, TestClient(app) as second:
        login(first, "multi-session@example.test")
        first_token = first.cookies.get(COOKIE_NAME)
        login(second, "multi-session@example.test")
        second_token = second.cookies.get(COOKIE_NAME)
        assert first_token != second_token

        logout = first.post("/logout")
        assert logout.status_code == 204
        assert first.cookies.get(COOKIE_NAME) is None

        first.cookies.set(COOKIE_NAME, first_token)
        rejected = first.get("/vehiculos")
        allowed = second.get("/vehiculos")
        assert rejected.status_code == 401
        assert rejected.json() == {"detail": "No autenticado"}
        assert allowed.status_code == 200

    with factory() as session:
        first_row = session.scalar(
            select(Sesion).where(Sesion.token_hash == hash_session_token(first_token))
        )
        second_row = session.scalar(
            select(Sesion).where(Sesion.token_hash == hash_session_token(second_token))
        )
        assert first_row.revocada_en is not None
        assert second_row.revocada_en is None


@pytest.mark.parametrize("failure", ["audit", "session"])
def test_security_control_failure_returns_503_and_never_executes_endpoint(
    security_database, monkeypatch, failure
):
    factory, database_url = security_database
    email = f"{failure}-failure@example.test"
    create_user(factory, email, "ADMINISTRADOR")
    app = security_app(database_url)

    with TestClient(app) as client:
        login(client, email)
        token = client.cookies.get(COOKIE_NAME)
        assert token

        if failure == "audit":

            def fail_audit(_record):
                raise AuditStorageError("private SQL and password details")

            monkeypatch.setattr(
                app.state.authorization_service._auditoria,
                "registrar",
                fail_audit,
            )
        else:

            def fail_session_storage(_repository, _token_hash):
                assert _token_hash == hash_session_token(token)
                raise SessionStorageError(
                    f"private SQL traceback {email} {token} {COOKIE_NAME}"
                )

            monkeypatch.setattr(
                SesionRepository,
                "find_identity",
                fail_session_storage,
            )

        response = client.post(
            "/vehiculos", json=vehicle_payload(f"FAIL-{failure[:1].upper()}")
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Servicio no disponible"}
    for restricted in (
        "private",
        "sql",
        "traceback",
        token,
        COOKIE_NAME,
        email,
        "password",
    ):
        assert restricted.lower() not in response.text.lower()
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Vehiculo)) == 0
        assert authorization_rows(session) == []
