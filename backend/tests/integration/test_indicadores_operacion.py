"""ECL-25 / RNF-012: /indicadores/operacion sobre PostgreSQL + PostGIS reales.

Regresión de CI con el dataset de ``scripts/indicadores_dataset.py`` (50 vehículos,
200 conductores y 30 000 pedidos): payload ≤ 250 000 bytes y número fijo de
sentencias SQL, igual con la base vacía que con el dataset.
"""

from contextlib import contextmanager
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, event, inspect
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.db.session import session_factory
from app.main import create_app
from app.models import Auditoria
from app.models.conductor import Conductor
from app.models.usuario import Usuario
from app.repositories.indicadores import IndicadoresRepository
from app.repositories.usuarios import UsuarioRepository
from app.services.conductores import ConductorService
from app.services.credenciales import CredentialService
from app.services.indicadores import IndicadoresService
from scripts.indicadores_dataset import expected, seed_operational_dataset

pytestmark = pytest.mark.integration

LIMA = ZoneInfo("America/Lima")
MAX_PAYLOAD_BYTES = 250_000
# Sesión (1) + autorización (1) + tres agregados; nunca depende de las filas.
FIXED_STATEMENTS = 5
PASSWORD = "correct-password"
ROLES = ("ADMINISTRADOR", "OPERADOR", "ANALISTA", "AUDITOR", "CONDUCTOR")


@contextmanager
def count_statements():
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(Engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(Engine, "before_cursor_execute", record)


@pytest.fixture
def indicators(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    with factory.begin() as session:
        for role in ROLES:
            CredentialService(UsuarioRepository(session)).create(
                f"{role.lower()}-indicadores@example.test", PASSWORD, role
            )
    app = create_app(
        Settings(app_env="test", database_url=config.attributes["database_url"])
    )
    try:
        with TestClient(app) as client:
            yield engine, factory, client
    finally:
        # La auditoría es de solo inserción; limpieza exclusiva del fixture.
        with factory.begin() as session:
            session.execute(delete(Auditoria))


def login(client, role):
    response = client.post(
        "/login",
        json={
            "email": f"{role.lower()}-indicadores@example.test",
            "password": PASSWORD,
        },
    )
    assert response.status_code == 200


def seed_dataset(engine):
    with Session(engine) as session:
        seed_operational_dataset(session, now=datetime.now(LIMA))
        session.commit()


def get_indicators(client):
    with count_statements() as statements:
        response = client.get("/indicadores/operacion")
    return response, statements


def test_ruta_dorada_dataset_realista_payload_y_valores(indicators):
    """Ruta dorada: 50/200/30 000 → agregados exactos y payload ≤ 250 000 B."""
    engine, _, client = indicators
    seed_dataset(engine)
    login(client, "ADMINISTRADOR")
    response, statements = get_indicators(client)
    assert response.status_code == 200
    assert len(response.content) <= MAX_PAYLOAD_BYTES
    assert len(statements) == FIXED_STATEMENTS, statements
    assert response.headers["cache-control"] == "private, max-age=30"
    body = response.json()
    target = expected()
    # Las 5 cuentas del fixture no son conductores: no alteran estos conteos.
    assert body["vehiculos"] == {
        "total": target.vehiculos_total,
        "activos": target.vehiculos_activos,
        "capacidad_kg_activa": f"{target.capacidad_kg_activa}.00",
    }
    assert body["conductores"] == {
        "total": target.conductores_total,
        "habilitados_asignacion": target.conductores_habilitados,
        "no_habilitados": target.conductores_total - target.conductores_habilitados,
    }
    assert body["pedidos"] == {
        "total": target.pedidos_total,
        "por_estado": {"PENDIENTE": target.pedidos_total},
        "por_prioridad": target.pedidos_por_prioridad,
    }
    text = response.text
    for personal in ("dni", "telefono", "nombre", "email", "@", "direccion"):
        assert personal not in text


def test_regresion_sentencias_fijas_con_base_vacia_y_con_dataset(indicators):
    """Regresión: mismas sentencias SQL con 0 filas que con 30 000 pedidos."""
    engine, _, client = indicators
    login(client, "ADMINISTRADOR")
    empty, empty_statements = get_indicators(client)
    seed_dataset(engine)
    full, full_statements = get_indicators(client)
    assert empty.status_code == full.status_code == 200
    assert len(empty_statements) == len(full_statements) == FIXED_STATEMENTS
    assert len(full.content) <= MAX_PAYLOAD_BYTES


@pytest.mark.parametrize("role", ["OPERADOR", "ANALISTA", "AUDITOR"])
def test_ruta_feliz_roles_con_alcance_general(indicators, role):
    _, _, client = indicators
    login(client, role)
    assert client.get("/indicadores/operacion").status_code == 200


def test_ruta_infeliz_sin_sesion_401_y_conductor_403(indicators):
    _, _, client = indicators
    anonymous = client.get("/indicadores/operacion")
    assert anonymous.status_code == 401
    login(client, "CONDUCTOR")
    denied = client.get("/indicadores/operacion")
    assert denied.status_code == 403
    assert denied.json() == {"detail": "Acceso denegado"}


def test_ruta_infeliz_fallo_de_base_503_saneado(indicators, monkeypatch):
    _, _, client = indicators
    login(client, "ADMINISTRADOR")

    def fail(self, now):
        raise OperationalError("SELECT interno", {}, Exception("credencial"))

    monkeypatch.setattr(IndicadoresRepository, "operational_counts", fail)
    response = client.get("/indicadores/operacion")
    assert response.status_code == 503
    assert response.json() == {"detail": "Servicio no disponible"}
    assert "interno" not in response.text and "credencial" not in response.text


def test_ruta_de_borde_base_vacia(indicators):
    _, _, client = indicators
    login(client, "ADMINISTRADOR")
    body = client.get("/indicadores/operacion").json()
    assert body["vehiculos"] == {"total": 0, "activos": 0, "capacidad_kg_activa": "0"}
    assert body["conductores"] == {
        "total": 0,
        "habilitados_asignacion": 0,
        "no_habilitados": 0,
    }
    assert body["pedidos"] == {
        "total": 0,
        "por_estado": {},
        "por_prioridad": {"EXPRESS": 0, "ESTANDAR": 0, "ECONOMICO": 0},
    }


def test_ruta_de_borde_mas_de_100_conductores_igual_regla_que_el_listado(indicators):
    """Borde: 200 conductores; el agregado SQL coincide con habilitado_asignacion."""
    engine, factory, client = indicators
    seed_dataset(engine)
    drivers = ConductorService(factory)
    listed = []
    page = 1
    while items := drivers.list_page(page, 100).items:
        listed.extend(items)
        page += 1
    assert len(listed) == 200
    login(client, "ADMINISTRADOR")
    body = client.get("/indicadores/operacion").json()["conductores"]
    assert body["total"] == len(listed)
    assert (
        body["habilitados_asignacion"]
        == sum(item.habilitado_asignacion for item in listed)
        == expected().conductores_habilitados
    )


def add_driver(factory, index, *, licence: date, until: datetime):
    with factory.begin() as session:
        account = Usuario(
            email=f"borde{index}@example.test",
            password_hash="no-usado",
            rol="CONDUCTOR",
            estado="ACTIVO",
        )
        session.add(account)
        session.flush()
        session.add(
            Conductor(
                usuario_id=account.usuario_id,
                nombre=f"Conductor borde {index}",
                dni=f"{90000000 + index}",
                licencia_numero=f"B{index:08d}",
                licencia_vigente_hasta=licence,
                experiencia_anios=1,
                telefono="+51900000001",
                disponible_desde=until - timedelta(hours=8),
                disponible_hasta=until,
                punto_partida="Almacén ficticio",
                estado="ACTIVO",
            )
        )


def test_ruta_de_borde_licencia_que_vence_hoy_y_disponibilidad_terminada(indicators):
    """Borde: licencia vigente hasta hoy (Lima) sí; disponibilidad ya terminada no."""
    _, factory, _ = indicators
    now = datetime(2026, 10, 14, 12, 0, tzinfo=LIMA)
    add_driver(factory, 1, licence=now.date(), until=now + timedelta(minutes=1))
    add_driver(
        factory,
        2,
        licence=now.date() - timedelta(days=1),
        until=now + timedelta(hours=1),
    )
    add_driver(factory, 3, licence=now.date(), until=now)
    result = IndicadoresService(factory, clock=lambda: now).operational()
    assert result.conductores.total == 3
    assert result.conductores.habilitados_asignacion == 1


def test_migracion_0011_crea_y_revierte_el_indice(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    index = {item["name"]: item for item in inspect(engine).get_indexes("pedido")}
    assert index["idx_pedido_estado_prioridad"]["column_names"] == [
        "estado",
        "prioridad",
    ]
    command.downgrade(config, "0010_extend_driver_audit_events")
    names = {item["name"] for item in inspect(engine).get_indexes("pedido")}
    assert "idx_pedido_estado_prioridad" not in names
