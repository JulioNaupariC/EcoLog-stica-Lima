"""ST-024: real login, permissions, durable writes and negative-case rollback."""

from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from test_conductor_http_e2e import PASSWORD, payload

from alembic import command
from app.core.config import Settings
from app.core.passwords import hash_password
from app.main import create_app
from app.models.auditoria import Auditoria
from app.models.conductor import Conductor
from app.models.usuario import Usuario
from app.schemas.conductor import ConductorResponse

pytestmark = pytest.mark.integration


@pytest.fixture
def driver_http(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    with Session(engine) as session:
        session.add(
            Usuario(
                email="admin@example.test",
                password_hash=hash_password(PASSWORD),
                rol="ADMINISTRADOR",
            )
        )
        session.commit()
    settings = Settings(database_url=engine.url.render_as_string(hide_password=False))
    try:
        with TestClient(create_app(settings)) as client:
            login(client, "admin@example.test")
            created = client.post("/conductores", json=payload())
            assert created.status_code == 201
            yield client, engine, settings, created.json()
    finally:
        # Audit is append-only during operation; fixture-only cleanup before downgrade.
        with Session(engine) as session:
            session.execute(delete(Auditoria))
            session.commit()


def login(client, email):
    response = client.post("/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200


def snapshot(engine):
    """Use a new connection to inspect committed business state, excluding audit."""
    with Session(engine) as session:
        return (
            session.scalar(select(func.count()).select_from(Usuario)),
            [
                tuple(row)
                for row in session.execute(
                    select(
                        Conductor.conductor_id,
                        Conductor.dni,
                        Conductor.nombre,
                        Conductor.disponible_desde,
                        Conductor.disponible_hasta,
                    ).order_by(Conductor.conductor_id)
                )
            ],
        )


def test_negative_requests_preserve_committed_data(driver_http):
    client, engine, _, created = driver_http
    path = "/conductores/" + created["conductor_id"]
    before = snapshot(engine)
    invalid_creates = [
        (payload(email="duplicate-dni@example.test"), 409),
        (payload(dni="87654321"), 409),
        (payload(dni="bad", email="invalid@example.test"), 422),
        (payload(rol="ADMINISTRADOR"), 422),
        (payload(disponible_desde=None), 422),
    ]
    for body, status in invalid_creates:
        response = client.post("/conductores", json=body)
        assert response.status_code == status
        assert PASSWORD not in response.text
        assert snapshot(engine) == before
    for changes in [
        {
            "disponible_desde": "2099-01-02T08:00:00Z",
            "disponible_hasta": "2099-01-01T08:00:00Z",
        },
        {"disponible_desde": None},
        {"nombre": None},
        {"usuario_id": created["usuario_id"]},
        {"email": "other@example.test"},
        {},
    ]:
        assert client.patch(path, json=changes).status_code == 422
        assert snapshot(engine) == before
    other = client.post(
        "/conductores", json=payload(dni="87654321", email="other@example.test")
    )
    assert other.status_code == 201
    before = snapshot(engine)
    # Another valid change in the same PATCH must also roll back on DNI conflict.
    assert (
        client.patch(path, json={"dni": "87654321", "nombre": "Rollback"}).status_code
        == 409
    )
    assert snapshot(engine) == before


def test_availability_and_profile_survive_application_restart(driver_http):
    client, engine, settings, created = driver_http
    path = "/conductores/" + created["conductor_id"]
    changes = {
        "nombre": "Nombre persistido",
        "telefono": "+51987654322",
        "punto_partida": "Nueva base",
        "experiencia_anios": 5,
        "disponible_desde": "2099-10-09T08:00:00-05:00",
        "disponible_hasta": "2099-10-09T17:00:00-05:00",
    }
    response = client.patch(path, json=changes)
    assert response.status_code == 200
    assert response.json()["habilitado_asignacion"] is True
    with Session(engine) as session:
        row = session.get(Conductor, UUID(created["conductor_id"]))
        assert row.nombre == changes["nombre"] and row.telefono == changes["telefono"]
        assert row.disponible_desde.astimezone(timezone.utc) == datetime(
            2099, 10, 9, 13, tzinfo=timezone.utc
        )
        assert row.disponible_hasta.astimezone(timezone.utc) == datetime(
            2099, 10, 9, 22, tzinfo=timezone.utc
        )
    # A new FastAPI instance owns a new pool/session factory and a new login cookie.
    with TestClient(create_app(settings)) as restarted:
        login(restarted, "admin@example.test")
        stored = restarted.get(path)
        assert stored.status_code == 200
        assert ConductorResponse.model_validate(stored.json()) == (
            ConductorResponse.model_validate(response.json())
        )
        cleared = restarted.patch(
            path, json={"disponible_desde": None, "disponible_hasta": None}
        )
        assert cleared.status_code == 200
        assert cleared.json()["habilitado_asignacion"] is False
    reread = client.get(path)
    assert reread.status_code == 200
    assert reread.json()["disponible_desde"] is None
    assert reread.json()["disponible_hasta"] is None
    assert reread.json()["habilitado_asignacion"] is False
    expired = client.patch(
        path,
        json={
            "licencia_vigente_hasta": "2000-01-01",
            "disponible_desde": changes["disponible_desde"],
            "disponible_hasta": changes["disponible_hasta"],
        },
    )
    assert expired.status_code == 200
    assert expired.json()["habilitado_asignacion"] is False
    assert client.get(path).json()["licencia_vigente_hasta"] == "2000-01-01"


@pytest.mark.parametrize("role", ["CONDUCTOR", "AUDITOR", "ANALISTA"])
def test_real_forbidden_writes_preserve_data_and_audit_denial(driver_http, role):
    client, engine, _, created = driver_http
    email = "driver@example.test"
    if role != "CONDUCTOR":
        email = role.lower() + "@example.test"
        with Session(engine) as session:
            session.add(
                Usuario(email=email, password_hash=hash_password(PASSWORD), rol=role)
            )
            session.commit()
    assert client.post("/logout").status_code == 204
    login(client, email)
    before = snapshot(engine)
    with Session(engine) as session:
        audit_before = session.scalar(select(func.count()).select_from(Auditoria))
    path = "/conductores/" + created["conductor_id"]
    assert (
        client.post(
            "/conductores", json=payload(dni="87654321", email="forbidden@example.test")
        ).status_code
        == 403
    )
    assert client.patch(path, json={"nombre": "No permitido"}).status_code == 403
    assert snapshot(engine) == before
    with Session(engine) as session:
        events = session.scalars(select(Auditoria).order_by(Auditoria.creado_en)).all()
        assert len(events) >= audit_before + 2
        assert sum(event.accion == "AUTORIZACION_DENEGADA" for event in events) >= 2


def test_revoked_session_cannot_read_or_write_drivers(driver_http):
    client, engine, _, created = driver_http
    token = client.cookies.get("ecologistica_session")
    assert token
    assert client.post("/logout").status_code == 204
    # Replaying the old cookie must fail even though its format is still valid.
    client.cookies.set("ecologistica_session", token)
    before = snapshot(engine)
    path = "/conductores/" + created["conductor_id"]
    assert client.get("/conductores").status_code == 401
    assert client.get(path).status_code == 401
    assert client.post("/conductores", json=payload()).status_code == 401
    assert client.patch(path, json={"nombre": "No permitido"}).status_code == 401
    assert snapshot(engine) == before
