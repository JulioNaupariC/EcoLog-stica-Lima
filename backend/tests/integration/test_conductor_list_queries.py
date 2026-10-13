"""ECL-64: el listado de conductores no ejecuta una consulta por fila (N+1).

Se cuentan las sentencias SQL reales emitidas por ``ConductorService.list_page``
sobre PostgreSQL con ``before_cursor_execute``. El límite es de 3 sentencias
por página, independiente de ``page_size``.
"""

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.models.conductor import Conductor
from app.models.usuario import Usuario
from app.services.conductores import ConductorService

pytestmark = pytest.mark.integration

MAX_QUERIES_PER_PAGE = 3


@contextmanager
def count_statements(engine):
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


def seed_drivers(engine, total, *, account_estado="ACTIVO", account_rol="CONDUCTOR"):
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        for index in range(total):
            account = Usuario(
                email=f"conductor{index}@example.test",
                password_hash="no-usado-en-esta-prueba",
                rol=account_rol,
                estado=account_estado,
            )
            session.add(account)
            session.flush()
            session.add(
                Conductor(
                    usuario_id=account.usuario_id,
                    nombre=f"Conductor ficticio {index}",
                    dni=f"{index:08d}",
                    licencia_numero=f"Q{index:08d}",
                    licencia_vigente_hasta=date(2099, 12, 31),
                    experiencia_anios=3,
                    telefono="+51900000000",
                    disponible_desde=now - timedelta(hours=1),
                    disponible_hasta=now + timedelta(days=1),
                    punto_partida="Almacén ficticio",
                    estado="ACTIVO",
                )
            )
        session.commit()


@pytest.fixture
def driver_listing(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    return engine, ConductorService(sessionmaker(engine))


def test_ruta_dorada_pagina_por_defecto_en_consultas_constantes(driver_listing):
    """Ruta dorada: página de 20 conductores elegibles con ≤ 3 sentencias."""
    engine, service = driver_listing
    seed_drivers(engine, 25)
    with count_statements(engine) as statements:
        page = service.list_page(1, 20)
    assert len(page.items) == 20 and page.total == 25
    assert all(item.habilitado_asignacion for item in page.items)
    assert len(statements) <= MAX_QUERIES_PER_PAGE, statements


@pytest.mark.parametrize("page_size", [1, 20, 100])
def test_ruta_feliz_consultas_independientes_de_page_size(driver_listing, page_size):
    """Ruta feliz: el número de sentencias no crece con ``page_size``."""
    engine, service = driver_listing
    seed_drivers(engine, 105)
    with count_statements(engine) as statements:
        page = service.list_page(1, page_size)
    assert len(page.items) == page_size
    assert len(statements) <= MAX_QUERIES_PER_PAGE, statements


def test_ruta_infeliz_cuenta_inactiva_no_habilita_y_no_agrega_consultas(
    driver_listing,
):
    """Ruta infeliz: cuentas inactivas se resuelven en el mismo join."""
    engine, service = driver_listing
    seed_drivers(engine, 5, account_estado="INACTIVO")
    with count_statements(engine) as statements:
        page = service.list_page(1, 20)
    assert page.total == 5
    assert not any(item.habilitado_asignacion for item in page.items)
    assert len(statements) <= MAX_QUERIES_PER_PAGE, statements


@pytest.mark.parametrize("existing,page,expected", [(0, 1, 0), (21, 2, 1), (3, 5, 0)])
def test_ruta_de_borde_tabla_vacia_ultima_pagina_y_fuera_de_rango(
    driver_listing, existing, page, expected
):
    """Ruta de borde: tabla vacía, última página parcial y página inexistente."""
    engine, service = driver_listing
    if existing:
        seed_drivers(engine, existing)
    with count_statements(engine) as statements:
        result = service.list_page(page, 20)
    assert len(result.items) == expected and result.total == existing
    assert len(statements) <= MAX_QUERIES_PER_PAGE, statements
