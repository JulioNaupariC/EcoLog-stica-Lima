"""ECL-73 / ST-040 over PostgreSQL/PostGIS with the real HTTP chain.

Login, opaque cookie, persisted session, RBAC, geography storage and audit.
Personal data and passwords here are synthetic and test-only.
"""

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.core.config import Settings
from app.core.incidencias import (
    OBSERVACION_MAX,
    OCURRIDA_MAX_ANTIGUEDAD,
    OCURRIDA_MAX_FUTURO,
    SEVERIDADES,
    TIPOS,
)
from app.db.session import session_factory
from app.main import create_app
from app.models import Auditoria, Incidencia
from app.repositories.auditoria import Evento
from app.repositories.usuarios import UsuarioRepository
from app.schemas.conductor import ConductorCreate
from app.services.conductores import ConductorService
from app.services.credenciales import CredentialService
from app.services.driver_reports import DriverReportService

pytestmark = pytest.mark.integration

PASSWORD = "synthetic-password-1"
DRIVER = "conductor-inc@example.test"
OTHER_DRIVER = "conductor-otro@example.test"
NOTE = "Llanta pinchada en Av. Arequipa"


@pytest.fixture
def incident_database(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    try:
        yield factory, config.attributes["database_url"]
    finally:
        # Disposable *_test evidence; 0013 refuses to downgrade while it exists.
        with factory.begin() as session:
            session.execute(delete(Incidencia))
            session.execute(delete(Auditoria))


def create_user(factory, email, role):
    with factory.begin() as session:
        return (
            CredentialService(UsuarioRepository(session))
            .create(email, PASSWORD, role)
            .usuario_id
        )


def create_driver(factory, admin_id, email, dni, name):
    now = datetime.now(timezone.utc)
    summary = ConductorService(factory).create(
        ConductorCreate(
            nombre=name,
            dni=dni,
            licencia_numero=f"Q-{dni}",
            licencia_vigente_hasta=date(now.year + 2, 12, 31),
            experiencia_anios=3,
            telefono="+51911111111" if dni.endswith("1") else "+51922222222",
            punto_partida="Base ficticia",
            disponible_desde=now - timedelta(hours=1),
            disponible_hasta=now + timedelta(days=1),
            email=email,
            password=PASSWORD,
        ),
        admin_id,
    )
    stop_id = uuid4()
    DriverReportService(factory).provision_assignment(
        stop_id=stop_id, owner_id=summary.usuario_id, position=1
    )
    return summary, stop_id


@pytest.fixture
def setup(incident_database):
    factory, url = incident_database
    admin_id = create_user(factory, "admin-inc@example.test", "ADMINISTRADOR")
    for role in ("OPERADOR", "ANALISTA", "AUDITOR"):
        create_user(factory, f"{role.lower()}-inc@example.test", role)
    driver, stop = create_driver(factory, admin_id, DRIVER, "70000001", "Rosa Prueba")
    _other, other_stop = create_driver(
        factory, admin_id, OTHER_DRIVER, "70000002", "Luis Prueba"
    )
    return {
        "factory": factory,
        "url": url,
        "driver": driver,
        "stop": stop,
        "other_stop": other_stop,
    }


def client_for(url):
    return TestClient(create_app(Settings(app_env="test", database_url=url)))


def login(client, email):
    response = client.post("/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return client


def body(**changes):
    values = {
        "operation_id": str(uuid4()),
        "tipo": "AVERIA",
        "severidad": "ALTA",
        "ocurrida_en": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
        "latitud": -12.0464,
        "longitud": -77.0428,
        "observacion": NOTE,
    }
    values.update(changes)
    return values


def incident_count(factory):
    with factory() as session:
        return session.scalar(select(func.count()).select_from(Incidencia))


def incident_audits(factory):
    with factory() as session:
        return list(
            session.scalars(
                select(Auditoria).where(
                    Auditoria.accion == Evento.INCIDENCIA_REGISTRADA.value
                )
            )
        )


def test_golden_driver_registers_pending_incident_audited_and_listed(setup):
    factory = setup["factory"]
    with client_for(setup["url"]) as driver, client_for(setup["url"]) as operator:
        login(driver, DRIVER)
        data = body(parada_id=str(setup["stop"]))
        response = driver.post("/conductor/incidencias", json=data)
        assert response.status_code == 201
        ack = response.json()
        assert ack["estado"] == "PENDIENTE_VALIDACION"
        assert ack["operation_id"] == data["operation_id"]
        assert ack["registrada_en"].endswith("-05:00")

        login(operator, "operador-inc@example.test")
        listing = operator.get("/incidencias")
    assert listing.status_code == 200
    [item] = listing.json()["items"]
    assert item["incidencia_id"] == ack["incidencia_id"]
    assert item["conductor"] == {
        "conductor_id": str(setup["driver"].conductor_id),
        "nombre": "Rosa Prueba",
    }
    assert (item["latitud"], item["longitud"]) == (-12.0464, -77.0428)
    assert item["observacion"] == NOTE
    for private in ("70000001", "+51911111111", "Q-70000001"):
        assert private not in listing.text

    with factory() as session:
        stored = session.get(Incidencia, ack["incidencia_id"])
        assert stored.conductor_id == setup["driver"].conductor_id
        assert stored.parada_id == setup["stop"]
        assert stored.estado == "PENDIENTE_VALIDACION"
        geography = session.scalar(
            text(
                "SELECT GeometryType(ubicacion::geometry) || ':' || "
                "ST_SRID(ubicacion::geometry) FROM incidencia"
            )
        )
        assert geography == "POINT:4326"
    [audit] = incident_audits(factory)
    assert audit.entidad == "incidencia"
    assert str(audit.entidad_id) == ack["incidencia_id"]
    assert audit.usuario_id == setup["driver"].usuario_id
    assert audit.detalle == {
        "tipo": "AVERIA",
        "severidad": "ALTA",
        "con_parada": True,
        "con_observacion": True,
    }


def test_happy_resend_same_operation_does_not_duplicate(setup):
    factory = setup["factory"]
    data = body()
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER)
        first = driver.post("/conductor/incidencias", json=data)
        second = driver.post("/conductor/incidencias", json=data)
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json() == second.json()
    assert incident_count(factory) == 1
    assert len(incident_audits(factory)) == 1


def test_unhappy_same_operation_with_different_content_is_409(setup):
    data = body()
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER)
        assert driver.post("/conductor/incidencias", json=data).status_code == 201
        conflict = driver.post(
            "/conductor/incidencias", json={**data, "severidad": "BAJA"}
        )
    assert conflict.status_code == 409
    assert incident_count(setup["factory"]) == 1


@pytest.mark.parametrize(
    "email",
    ["admin-inc@example.test", "analista-inc@example.test", "auditor-inc@example.test"],
)
def test_unhappy_roles_without_permission_cannot_register(setup, email):
    with client_for(setup["url"]) as client:
        login(client, email)
        response = client.post("/conductor/incidencias", json=body())
    assert response.status_code == 403
    assert incident_count(setup["factory"]) == 0


@pytest.mark.parametrize(
    "email",
    ["analista-inc@example.test", "auditor-inc@example.test", DRIVER],
)
def test_unhappy_roles_without_general_scope_cannot_list(setup, email):
    factory = setup["factory"]
    with client_for(setup["url"]) as client:
        login(client, email)
        response = client.get("/incidencias")
    assert response.status_code == 403
    with factory() as session:
        denied = session.scalars(
            select(Auditoria).where(Auditoria.accion == Evento.DENEGADA.value)
        ).all()
    assert any(row.detalle["permiso"] == "incidencias.consultar" for row in denied)


def test_unhappy_without_session_is_401(setup):
    with client_for(setup["url"]) as client:
        assert client.post("/conductor/incidencias", json=body()).status_code == 401
        assert client.get("/incidencias").status_code == 401


def _shifted(delta: timedelta) -> str:
    # Computed when the test runs, not at collection time (the suite is slow).
    return (datetime.now(timezone.utc) + delta).isoformat()


@pytest.mark.parametrize(
    "changes",
    [
        {"ocurrida_en": lambda: _shifted(OCURRIDA_MAX_FUTURO + timedelta(minutes=1))},
        {
            "ocurrida_en": lambda: _shifted(
                -OCURRIDA_MAX_ANTIGUEDAD - timedelta(minutes=1)
            )
        },
        {"ocurrida_en": "2026-10-27T09:15:00"},
        {"latitud": 95.5},
        {"longitud": -181.25},
        {"observacion": "z" * (OBSERVACION_MAX + 1)},
        {"tipo": "INCENDIO"},
        {"severidad": "CRITICA"},
    ],
    ids=[
        "futuro",
        "antigua",
        "sin-zona",
        "latitud",
        "longitud",
        "observacion",
        "tipo",
        "severidad",
    ],
)
def test_edge_invalid_data_is_422_without_echo_or_persistence(setup, changes):
    changes = {
        key: value() if callable(value) else value for key, value in changes.items()
    }
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER)
        response = driver.post("/conductor/incidencias", json=body(**changes))
    assert response.status_code == 422
    assert NOTE not in response.text
    for value in changes.values():
        assert str(value) not in response.text
    assert incident_count(setup["factory"]) == 0
    assert incident_audits(setup["factory"]) == []


def test_edge_stop_of_another_driver_is_422(setup):
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER)
        response = driver.post(
            "/conductor/incidencias",
            json=body(parada_id=str(setup["other_stop"])),
        )
    assert response.status_code == 422
    assert incident_count(setup["factory"]) == 0


def test_edge_list_orders_by_occurrence_desc_and_paginates(setup):
    now = datetime.now(timezone.utc)
    with client_for(setup["url"]) as driver, client_for(setup["url"]) as admin:
        login(driver, DRIVER)
        for minutes, tipo in ((30, "TRAFICO"), (5, "CLIMA"), (60, "OTRO")):
            data = body(
                tipo=tipo, ocurrida_en=(now - timedelta(minutes=minutes)).isoformat()
            )
            assert driver.post("/conductor/incidencias", json=data).status_code == 201
        login(admin, "admin-inc@example.test")
        first = admin.get("/incidencias", params={"page_size": 2}).json()
        second = admin.get("/incidencias", params={"page": 2, "page_size": 2}).json()
        others = admin.get("/incidencias", params={"estado": "VALIDADA"}).json()
    assert [item["tipo"] for item in first["items"]] == ["CLIMA", "TRAFICO"]
    assert [item["tipo"] for item in second["items"]] == ["OTRO"]
    assert (first["total"], second["total"], others["total"]) == (3, 3, 0)


def test_0013_upgrade_downgrade_upgrade_single_head_and_catalogues(migration_database):
    engine, config = migration_database
    assert ScriptDirectory.from_config(config).get_heads() == ["0013_incidencias"]
    command.upgrade(config, "0013_incidencias")
    with engine.connect() as connection:
        checks = dict(
            connection.execute(
                text(
                    "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid = 'incidencia'::regclass AND contype = 'c'"
                )
            ).all()
        )
        for value in TIPOS:
            assert value in checks["ck_incidencia_tipo"]
        for value in SEVERIDADES:
            assert value in checks["ck_incidencia_severidad"]
        assert "PENDIENTE_VALIDACION" in checks["ck_incidencia_estado"]
        index = connection.scalar(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE indexname = 'ix_incidencia_estado_ocurrida'"
            )
        )
        assert "(estado, ocurrida_en DESC)" in index
        audit = connection.scalar(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'ck_auditoria_accion'"
            )
        )
        for action in ("INCIDENCIA_REGISTRADA", "CONTRASENA_CAMBIADA", "LOGIN_EXITOSO"):
            assert action in audit
    command.downgrade(config, "0012_password_reset")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT to_regclass('incidencia')")) is None
    command.upgrade(config, "head")
    command.check(config)


def test_0013_downgrade_rejects_and_preserves_incidents(setup, migration_database):
    factory = setup["factory"]
    _engine, config = migration_database
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER)
        assert driver.post("/conductor/incidencias", json=body()).status_code == 201
    with pytest.raises(IntegrityError, match="require manual treatment"):
        command.downgrade(config, "0012_password_reset")
    assert incident_count(factory) == 1
    assert len(incident_audits(factory)) == 1
