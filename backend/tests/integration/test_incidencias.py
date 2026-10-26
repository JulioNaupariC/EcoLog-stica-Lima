"""ECL-73 over PostgreSQL/PostGIS against the ECL-72 BDD (I01–I11, I13–I16).

Real chain: login, opaque cookie, persisted session, RBAC, geography storage
and audit. The server clock is fixed at T0 = 2026-10-27T09:16:02-05:00, the BDD
fixture. Personal data and passwords are synthetic and test-only. I12 (offline
10/10) belongs to the interface and is covered by ECL-74 and ECL-76.
"""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from uuid import uuid1, uuid4
from zoneinfo import ZoneInfo

import pytest
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.core.config import Settings
from app.core.incidencias import (
    OBSERVACION_MAX,
    OCURRIDA_MAX_FUTURO,
    PAGE_SIZE_MAX,
    SEVERIDADES,
    TIPOS,
)
from app.db.session import session_factory
from app.main import create_app
from app.models import Auditoria, Incidencia
from app.repositories.auditoria import Evento
from app.repositories.incidencias import IncidenciaRepository
from app.repositories.usuarios import UsuarioRepository
from app.schemas.conductor import ConductorCreate
from app.services import incidencias as incident_service
from app.services.conductores import ConductorService
from app.services.credenciales import CredentialService
from app.services.driver_reports import DriverReportService

pytestmark = pytest.mark.integration

LIMA = ZoneInfo("America/Lima")
T0 = datetime(2026, 10, 27, 9, 16, 2, tzinfo=LIMA)
PASSWORD = "synthetic-password-1"
DRIVER_A = "conductor-a@example.test"
DRIVER_B = "conductor-b@example.test"
UNLINKED_DRIVER = "conductor-sin-perfil@example.test"
NOTE = "Llanta pinchada: reporte de prueba"
FIXTURE = {
    "operation_id": "2d7d7ad5-57e1-4b17-9c8d-5094a6fc7a01",
    "tipo": "AVERIA",
    "severidad": "ALTA",
    "ocurrida_en": "2026-10-27T09:15:00-05:00",
    "latitud": -12.0464,
    "longitud": -77.0428,
    "observacion": NOTE,
}


@pytest.fixture
def incident_database(migration_database, monkeypatch):
    engine, config = migration_database
    command.upgrade(config, "head")
    monkeypatch.setattr(incident_service, "utc_now", lambda: T0)
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


def create_driver(factory, admin_id, email, dni, name, phone):
    now = datetime.now(timezone.utc)
    summary = ConductorService(factory).create(
        ConductorCreate(
            nombre=name,
            dni=dni,
            licencia_numero=f"Q-{dni}",
            licencia_vigente_hasta=date(now.year + 2, 12, 31),
            experiencia_anios=3,
            telefono=phone,
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
    create_user(factory, UNLINKED_DRIVER, "CONDUCTOR")
    driver_a, stop_a = create_driver(
        factory, admin_id, DRIVER_A, "70000001", "Rosa Prueba", "+51911111111"
    )
    driver_b, stop_b = create_driver(
        factory, admin_id, DRIVER_B, "70000002", "Luis Prueba", "+51922222222"
    )
    return {
        "factory": factory,
        "url": url,
        "driver_a": driver_a,
        "driver_b": driver_b,
        "stop_a": stop_a,
        "stop_b": stop_b,
    }


def client_for(url):
    return TestClient(create_app(Settings(app_env="test", database_url=url)))


def login(client, email):
    response = client.post("/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return client


def body(**changes):
    values = {**FIXTURE, "operation_id": str(uuid4())}
    values.update(changes)
    return values


def post(client, data):
    # Raw JSON so key order and literal numbers (-12 vs -12.0) are preserved.
    return client.post(
        "/conductor/incidencias",
        content=json.dumps(data),
        headers={"Content-Type": "application/json"},
    )


def incidents(factory):
    with factory() as session:
        return list(session.scalars(select(Incidencia)))


def incident_audits(factory):
    with factory() as session:
        return list(
            session.scalars(
                select(Auditoria).where(
                    Auditoria.accion == Evento.INCIDENCIA_REGISTRADA.value
                )
            )
        )


def assert_nothing_stored(factory):
    assert incidents(factory) == []
    assert incident_audits(factory) == []


# --- Ruta dorada --------------------------------------------------------------


def test_I01_registrar_incidencia_valida_sin_ruta(setup):
    factory = setup["factory"]
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER_A)
        response = post(driver, FIXTURE)
    assert response.status_code == 201
    ack = response.json()
    assert set(ack) == {"incidencia_id", "operation_id", "estado", "registrada_en"}
    assert ack["operation_id"] == FIXTURE["operation_id"]
    assert ack["estado"] == "PENDIENTE_VALIDACION"
    assert ack["registrada_en"].endswith("-05:00")
    [stored] = incidents(factory)
    assert stored.conductor_id == setup["driver_a"].conductor_id
    assert stored.parada_id is None
    assert stored.observacion == NOTE
    with factory() as session:
        point = session.execute(
            text(
                "SELECT ST_Y(ubicacion::geometry), ST_X(ubicacion::geometry), "
                "ST_SRID(ubicacion::geometry) FROM incidencia"
            )
        ).one()
    assert tuple(point) == (-12.0464, -77.0428, 4326)
    [audit] = incident_audits(factory)
    assert (audit.entidad, str(audit.entidad_id)) == (
        "incidencia",
        ack["incidencia_id"],
    )
    assert audit.usuario_id == setup["driver_a"].usuario_id
    assert audit.detalle == {
        "tipo": "AVERIA",
        "severidad": "ALTA",
        "con_parada": False,
        "con_observacion": True,
    }


# --- Ruta feliz ------------------------------------------------------------------


@pytest.mark.parametrize(
    "email", ["admin-inc@example.test", "operador-inc@example.test"]
)
def test_I02_operacion_consulta_pendientes_ordenados_y_paginados(setup, email):
    with client_for(setup["url"]) as driver_a, client_for(setup["url"]) as driver_b:
        login(driver_a, DRIVER_A)
        login(driver_b, DRIVER_B)
        tie = "2026-10-27T08:00:00-05:00"
        for client, ocurrida_en in (
            (driver_a, "2026-10-27T09:00:00-05:00"),
            (driver_a, tie),
            (driver_b, tie),
            (driver_b, "2026-10-26T23:30:00-05:00"),
        ):
            assert post(client, body(ocurrida_en=ocurrida_en)).status_code == 201
    with client_for(setup["url"]) as operation:
        login(operation, email)
        full = operation.get("/incidencias").json()
        pages = [
            operation.get("/incidencias", params={"page": n, "page_size": 2}).json()
            for n in (1, 2)
        ]
    assert (full["page"], full["page_size"], full["total"]) == (1, 20, 4)
    items = full["items"]
    instants = [datetime.fromisoformat(item["ocurrida_en"]) for item in items]
    assert instants == sorted(instants, reverse=True)
    tied = [item["incidencia_id"] for item in items[1:3]]
    assert tied == sorted(tied)  # Tie broken by incidencia_id ascending.
    paged = [item["incidencia_id"] for page in pages for item in page["items"]]
    assert paged == [item["incidencia_id"] for item in items]
    assert len(set(paged)) == 4
    assert set(items[0]) == {
        "incidencia_id",
        "tipo",
        "severidad",
        "ocurrida_en",
        "registrada_en",
        "conductor",
        "latitud",
        "longitud",
        "observacion",
        "estado",
    }
    assert {item["conductor"]["nombre"] for item in items} == {
        "Rosa Prueba",
        "Luis Prueba",
    }
    raw = json.dumps(full)
    for private in ("70000001", "70000002", "+51911111111", "Q-70000001"):
        assert private not in raw


def test_I03_registrar_con_parada_propia(setup):
    factory = setup["factory"]
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER_A)
        response = post(driver, body(parada_id=str(setup["stop_a"])))
    assert response.status_code == 201
    [stored] = incidents(factory)
    assert (stored.parada_id, stored.conductor_id) == (
        setup["stop_a"],
        setup["driver_a"].conductor_id,
    )
    assert stored.estado == "PENDIENTE_VALIDACION"
    with factory() as session:
        stop_status = session.scalar(
            text("SELECT status FROM driver_stop_assignment WHERE stop_id = :id"),
            {"id": setup["stop_a"]},
        )
    assert stop_status == "PENDIENTE"  # Registering does not touch the stop.


# --- Ruta infeliz -------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing",
    [
        ["operation_id"],
        ["tipo"],
        ["severidad"],
        ["ocurrida_en"],
        ["latitud"],
        ["longitud"],
        ["tipo", "severidad", "latitud"],
    ],
    ids=lambda fields: "+".join(fields),
)
def test_I04_campos_obligatorios_ausentes_422_sin_reserva(setup, missing):
    data = {key: value for key, value in body().items() if key not in missing}
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER_A)
        response = post(driver, data)
        assert response.status_code == 422
        assert NOTE not in response.text
        assert_nothing_stored(setup["factory"])
        # The operation_id was not reserved: the complete report is accepted.
        if "operation_id" not in missing:
            complete = {**FIXTURE, "operation_id": data["operation_id"]}
            assert post(driver, complete).status_code == 201


@pytest.mark.parametrize(
    "ocurrida_en",
    [
        (T0 + OCURRIDA_MAX_FUTURO + timedelta(seconds=1)).isoformat(),
        "2026-10-27T09:15:00",
    ],
    ids=["T0+5min+1s", "sin-zona"],
)
def test_I05_hora_futura_o_sin_zona_422(setup, ocurrida_en):
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER_A)
        response = post(driver, body(ocurrida_en=ocurrida_en))
    assert response.status_code == 422
    assert ocurrida_en not in response.text
    assert_nothing_stored(setup["factory"])


def test_I06_observacion_de_501_puntos_de_codigo_422_sin_truncar(setup):
    text_501 = "ñ" * (OBSERVACION_MAX + 1)
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER_A)
        response = post(driver, body(observacion=text_501))
    assert response.status_code == 422
    assert "ñ" * 20 not in response.text
    assert_nothing_stored(setup["factory"])


@pytest.mark.parametrize(
    "changes",
    [
        {"tipo": "DESVIO"},
        {"severidad": "URGENTE"},
        {"tipo": ""},
        {"latitud": 90.0001},
        {"latitud": -90.0001},
        {"longitud": 180.0001},
        {"longitud": -180.0001},
        {"latitud": True},
        {"longitud": "-77.0428"},
        {"operation_id": "no-es-uuid"},
        {"operation_id": str(uuid1())},
        {"parada_id": "parada-mal-formada"},
        {"parada_id": str(uuid4())},
        {"conductor_id": str(uuid4())},
        {"usuario_id": str(uuid4())},
        {"reportada_por": str(uuid4())},
        {"ruta_id": str(uuid4())},
        {"estado": "VALIDADA"},
    ],
    ids=[
        "tipo",
        "severidad",
        "tipo-vacio",
        "lat-max",
        "lat-min",
        "lon-max",
        "lon-min",
        "lat-booleano",
        "lon-cadena",
        "uuid-mal-formado",
        "uuid-v1",
        "parada-mal-formada",
        "parada-inexistente",
        "conductor_id",
        "usuario_id",
        "reportada_por",
        "ruta_id",
        "estado",
    ],
)
def test_I07_variaciones_invalidas_422_sin_persistencia_ni_eco(setup, changes):
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER_A)
        response = post(driver, body(**changes))
    assert response.status_code == 422
    for value in changes.values():
        if isinstance(value, str) and value:
            assert value not in response.text
    assert NOTE not in response.text
    assert_nothing_stored(setup["factory"])


@pytest.mark.parametrize(
    "email",
    [
        "admin-inc@example.test",
        "operador-inc@example.test",
        "analista-inc@example.test",
        "auditor-inc@example.test",
    ],
)
def test_I08_crear_con_rol_sin_permiso_403(setup, email):
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER_A)
        assert post(driver, FIXTURE).status_code == 201
    with client_for(setup["url"]) as client:
        login(client, email)
        response = post(client, FIXTURE)  # Even with a known operation_id.
    assert response.status_code == 403
    assert response.json() == {"detail": "Acceso denegado"}
    assert len(incidents(setup["factory"])) == 1


@pytest.mark.parametrize(
    "email", ["analista-inc@example.test", "auditor-inc@example.test", DRIVER_A]
)
def test_I09_analista_auditor_o_conductor_no_listan(setup, email):
    factory = setup["factory"]
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER_A)
        assert post(driver, body()).status_code == 201
    with client_for(setup["url"]) as client:
        login(client, email)
        response = client.get("/incidencias")
    assert response.status_code == 403
    assert response.json() == {"detail": "Acceso denegado"}
    for leaked in ("items", "total", "Rosa"):
        assert leaked not in response.text
    with factory() as session:
        denied = session.scalars(
            select(Auditoria).where(Auditoria.accion == Evento.DENEGADA.value)
        ).all()
    assert any(row.detalle["permiso"] == "incidencias.consultar" for row in denied)


def test_I10_sin_sesion_401_en_ambos_endpoints(setup):
    with client_for(setup["url"]) as client:
        assert post(client, body()).status_code == 401
        assert client.get("/incidencias").status_code == 401
        client.cookies.set("ecologistica_session", "sesion-invalida")
        assert post(client, body()).status_code == 401
        assert client.get("/incidencias").status_code == 401
    assert_nothing_stored(setup["factory"])


def test_I10_parada_de_otro_conductor_403_generico(setup):
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER_A)
        response = post(driver, body(parada_id=str(setup["stop_b"])))
    assert response.status_code == 403
    assert response.json() == {"detail": "Acceso denegado"}
    assert "Luis" not in response.text
    assert_nothing_stored(setup["factory"])


def test_I10_conductor_sin_perfil_vinculado_403(setup):
    with client_for(setup["url"]) as client:
        login(client, UNLINKED_DRIVER)
        response = post(client, body())
    assert response.status_code == 403
    assert response.json() == {"detail": "Acceso denegado"}
    assert_nothing_stored(setup["factory"])


@pytest.mark.parametrize(
    "changes",
    [
        {"tipo": "TRAFICO"},
        {"severidad": "BAJA"},
        {"ocurrida_en": "2026-10-27T09:14:00-05:00"},
        {"latitud": -12.05},
        {"longitud": -77.05},
        {"parada_id": "stop_a"},
        {"observacion": "Otra observación válida"},
    ],
    ids=["tipo", "severidad", "hora", "latitud", "longitud", "parada", "observacion"],
)
def test_I11_mismo_operation_id_otro_contenido_devuelve_409(setup, changes):
    if changes.get("parada_id") == "stop_a":
        changes = {"parada_id": str(setup["stop_a"])}
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER_A)
        assert post(driver, FIXTURE).status_code == 201
        response = post(driver, {**FIXTURE, **changes})
    assert response.status_code == 409
    assert NOTE not in response.text and "AVERIA" not in response.text
    [stored] = incidents(setup["factory"])
    assert (stored.tipo, stored.severidad, stored.parada_id, stored.observacion) == (
        "AVERIA",
        "ALTA",
        None,
        NOTE,
    )
    assert len(incident_audits(setup["factory"])) == 1


# --- Ruta de borde -----------------------------------------------------------------


def test_I13_replay_equivalente_devuelve_la_respuesta_original(setup):
    factory = setup["factory"]
    original = {**FIXTURE, "latitud": -12, "longitud": -77, "observacion": None}
    replays = [
        dict(reversed(list(original.items()))),  # JSON key order.
        {**original, "ocurrida_en": "2026-10-27T14:15:00Z"},  # Same UTC instant.
        {**original, "latitud": -12.0, "longitud": -77.0},  # Numerically equal.
        {k: v for k, v in original.items() if k != "observacion"},  # Omitted.
        {**original, "observacion": ""},  # Normalized empty.
    ]
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER_A)
        first = post(driver, original)
        answers = [post(driver, replay) for replay in replays]
    assert first.status_code == 201
    assert [answer.status_code for answer in answers] == [200] * len(replays)
    assert all(answer.json() == first.json() for answer in answers)
    assert len(incidents(factory)) == 1
    assert len(incident_audits(factory)) == 1


def test_I13_dos_primeros_envios_concurrentes_un_201_y_un_200(setup, monkeypatch):
    factory = setup["factory"]
    # Both requests see "not stored yet" before either inserts: a real race.
    barrier = threading.Barrier(2, timeout=15)
    lock = threading.Lock()
    lookups = {"count": 0}
    original_find = IncidenciaRepository.find_by_operation

    def gated_find(self, conductor_id, operation_id):
        found = original_find(self, conductor_id, operation_id)
        with lock:
            lookups["count"] += 1
            first_two = lookups["count"] <= 2
        if found is None and first_two:
            barrier.wait()
        return found

    monkeypatch.setattr(IncidenciaRepository, "find_by_operation", gated_find)
    data = body()
    clients = [client_for(setup["url"]) for _ in range(2)]
    for client in clients:
        client.__enter__()
        login(client, DRIVER_A)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda client: post(client, data), clients))
    finally:
        for client in clients:
            client.__exit__(None, None, None)
    assert sorted(response.status_code for response in responses) == [200, 201]
    assert responses[0].json() == responses[1].json()
    assert len(incidents(factory)) == 1
    assert len(incident_audits(factory)) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"observacion": None},
        {"observacion": ""},
        {"observacion": "😀" * OBSERVACION_MAX},
        {"observacion": "  con espacios y MAYÚSCULAS  "},
        {"ocurrida_en": T0.isoformat()},
        {"ocurrida_en": (T0 + OCURRIDA_MAX_FUTURO).isoformat()},
        {"ocurrida_en": "2020-01-01T00:00:00-05:00"},
        {"latitud": 90, "longitud": 180},
        {"latitud": -90, "longitud": -180},
    ],
    ids=[
        "obs-null",
        "obs-vacia",
        "obs-500",
        "obs-exacta",
        "T0",
        "T0+5min",
        "pasada-sin-maximo",
        "extremos-max",
        "extremos-min",
    ],
)
def test_I14_limites_validos_se_aceptan_y_conservan(setup, changes):
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER_A)
        response = post(driver, body(**changes))
    assert response.status_code == 201
    [stored] = incidents(setup["factory"])
    if "observacion" in changes:
        assert stored.observacion == (changes["observacion"] or "")


def test_I14_observacion_omitida_se_guarda_vacia(setup):
    data = {k: v for k, v in body().items() if k != "observacion"}
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER_A)
        assert post(driver, data).status_code == 201
    assert incidents(setup["factory"])[0].observacion == ""


def test_I14_matriz_seis_tipos_por_tres_severidades(setup):
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER_A)
        codes = [
            post(driver, body(tipo=tipo, severidad=severidad)).status_code
            for tipo in TIPOS
            for severidad in SEVERIDADES
        ]
    assert codes == [201] * 18
    assert {row.estado for row in incidents(setup["factory"])} == {
        "PENDIENTE_VALIDACION"
    }


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 0},
        {"page_size": PAGE_SIZE_MAX + 1},
        {"page": "dos"},
        {"estado": "VALIDADA"},
    ],
)
def test_I15_paginacion_invalida_422(setup, params):
    with client_for(setup["url"]) as operation:
        login(operation, "operador-inc@example.test")
        response = operation.get("/incidencias", params=params)
    assert response.status_code == 422
    assert "items" not in response.text


def test_I15_lista_vacia_y_pagina_posterior_a_la_ultima(setup):
    with client_for(setup["url"]) as operation:
        login(operation, "admin-inc@example.test")
        empty = operation.get("/incidencias", params={"page_size": PAGE_SIZE_MAX})
        with client_for(setup["url"]) as driver:
            login(driver, DRIVER_A)
            assert post(driver, body()).status_code == 201
        beyond = operation.get("/incidencias", params={"page": 5, "page_size": 100})
    assert empty.status_code == beyond.status_code == 200
    assert empty.json() == {"items": [], "page": 1, "page_size": 100, "total": 0}
    assert beyond.json() == {"items": [], "page": 5, "page_size": 100, "total": 1}


def test_I16_mismo_uuid_de_otro_conductor_es_independiente(setup):
    factory = setup["factory"]
    with client_for(setup["url"]) as driver_a, client_for(setup["url"]) as driver_b:
        login(driver_a, DRIVER_A)
        login(driver_b, DRIVER_B)
        from_a = post(driver_a, FIXTURE)
        from_b = post(driver_b, {**FIXTURE, "tipo": "CLIMA", "observacion": "B"})
    assert (from_a.status_code, from_b.status_code) == (201, 201)
    assert from_a.json()["incidencia_id"] != from_b.json()["incidencia_id"]
    assert NOTE not in from_b.text
    owners = {row.conductor_id: row.tipo for row in incidents(factory)}
    assert owners == {
        setup["driver_a"].conductor_id: "AVERIA",
        setup["driver_b"].conductor_id: "CLIMA",
    }


# --- Migración 0013 -----------------------------------------------------------


def test_0013_upgrade_downgrade_upgrade_una_sola_cabeza(migration_database):
    engine, config = migration_database
    assert ScriptDirectory.from_config(config).get_heads() == ["0013_incidencias"]
    command.upgrade(config, "0013_incidencias")
    with engine.connect() as connection:
        constraints = dict(
            connection.execute(
                text(
                    "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid = 'incidencia'::regclass"
                )
            ).all()
        )
        assert constraints["uq_incidencia_conductor_operation"] == (
            "UNIQUE (conductor_id, operation_id)"
        )
        for value in TIPOS:
            assert value in constraints["ck_incidencia_tipo"]
        for value in SEVERIDADES:
            assert value in constraints["ck_incidencia_severidad"]
        assert "PENDIENTE_VALIDACION" in constraints["ck_incidencia_estado"]
        observacion = connection.execute(
            text(
                "SELECT is_nullable, column_default FROM information_schema.columns "
                "WHERE table_name = 'incidencia' AND column_name = 'observacion'"
            )
        ).one()
        assert observacion.is_nullable == "NO"
        assert observacion.column_default.startswith("''")
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


def test_0013_downgrade_protegido_conserva_incidencias(setup, migration_database):
    factory = setup["factory"]
    _engine, config = migration_database
    with client_for(setup["url"]) as driver:
        login(driver, DRIVER_A)
        assert post(driver, body()).status_code == 201
    with pytest.raises(IntegrityError, match="require manual treatment"):
        command.downgrade(config, "0012_password_reset")
    assert len(incidents(factory)) == 1
    assert len(incident_audits(factory)) == 1
