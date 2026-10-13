"""scripts/seed_demo.py sobre PostgreSQL real: datos, rutas de borde e idempotencia."""

from datetime import datetime

import pytest
from sqlalchemy import delete, func, select

from alembic import command
from app.core.rbac import Rol
from app.db.session import session_factory
from app.models import Auditoria, Cliente, Pedido
from app.models.conductor import Conductor
from app.models.driver_stop_assignment import DriverStopAssignment
from app.models.usuario import Usuario
from app.models.vehiculo import Vehiculo
from app.services.conductores import ConductorService
from app.services.driver_reports import DriverReportService
from scripts.seed_demo import DRIVERS, LIMA, seed

pytestmark = pytest.mark.integration

PASSWORDS = {role: f"demo-{role.value.lower()}-password" for role in Rol}
NOW = datetime(2026, 10, 13, 10, 0, tzinfo=LIMA)


@pytest.fixture
def demo_factory(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    try:
        yield factory
    finally:
        # Audit is append-only in the app; fixture-only cleanup before downgrade.
        with factory.begin() as session:
            session.execute(delete(Auditoria))


def counts(factory):
    with factory() as session:
        return {
            model.__tablename__: session.scalar(select(func.count()).select_from(model))
            for model in (
                Usuario,
                Cliente,
                Vehiculo,
                Conductor,
                Pedido,
                DriverStopAssignment,
            )
        }


def test_ruta_dorada_crea_el_conjunto_completo(demo_factory):
    summary = seed(demo_factory, PASSWORDS, now=NOW)
    assert counts(demo_factory) == {
        "usuario": 8,
        "cliente": 8,
        "vehiculo": 5,
        "conductor": 4,
        "pedido": 20,
        "driver_stop_assignment": 5,
    }
    assert summary.existing == {}


def test_ruta_feliz_conductor_demo_ve_su_itinerario_real(demo_factory):
    seed(demo_factory, PASSWORDS, now=NOW)
    with demo_factory() as session:
        owner = session.scalar(
            select(Conductor.usuario_id).where(Conductor.dni == DRIVERS[0].dni)
        )
    stops = DriverReportService(demo_factory).list_assignments(owner)
    assert [stop.position for stop in stops] == [1, 2, 3, 4, 5]
    assert all(stop.delivery is not None for stop in stops)


def test_ruta_de_borde_licencia_vencida_y_sin_disponibilidad(demo_factory):
    seed(demo_factory, PASSWORDS, now=NOW)
    page = ConductorService(demo_factory).list_page(1, 20)
    eligible = {item.nombre: item.habilitado_asignacion for item in page.items}
    assert eligible["Conductor Demo Licencia Vencida"] is False
    assert eligible["Conductora Demo Sin Disponibilidad"] is False
    assert eligible["Conductora Demo Uno"] is True
    with demo_factory() as session:
        audited = session.scalars(
            select(Auditoria.accion).where(Auditoria.entidad == "conductor")
        ).all()
    assert audited.count("CONDUCTOR_REGISTRADO") == 4
    assert audited.count("CONDUCTOR_ACTUALIZADO") == 1


def test_ruta_infeliz_segunda_ejecucion_no_duplica(demo_factory):
    seed(demo_factory, PASSWORDS, now=NOW)
    before = counts(demo_factory)
    summary = seed(demo_factory, PASSWORDS, now=NOW)
    assert counts(demo_factory) == before
    assert summary.created == {}
    assert summary.existing["pedidos"] == 20
    assert summary.existing["asignaciones"] == 5
