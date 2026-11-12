"""ECL-105: escenario de la demo del MVP sobre PostgreSQL real.

Siembra, idempotencia, rechazo de una fecha ocupada y una optimización real
corta (2 s) que deja los dos pedidos inviables sin asignar con su motivo.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select

from alembic import command
from app.core.rbac import Rol
from app.db.session import session_factory
from app.models import (
    Auditoria,
    Cliente,
    Incidencia,
    Optimizacion,
    ParadaRuta,
    Parametro,
    ParametroVersion,
    Pedido,
    PedidoNoAsignado,
    Ruta,
)
from app.optimizacion.sinteticos import DEPOSITO
from app.repositories.usuarios import UsuarioRepository
from app.schemas.rutas import OptimizacionSolicitud
from app.services.optimizaciones import OptimizacionService, medianoche
from scripts.seed_demo import LIMA, USERS
from scripts.seed_demo_mvp import (
    PREFIJO_PEDIDO,
    SeedMvpRefused,
    resumen_fecha,
    seed_mvp,
)

pytestmark = pytest.mark.integration

PASSWORDS = {role: f"demo-{role.value.lower()}-password" for role in Rol}
NOW = datetime(2026, 11, 11, 10, 0, tzinfo=LIMA)
FECHA = date(2026, 11, 20)


@pytest.fixture
def demo_factory(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    try:
        yield factory
    finally:
        # Fixture-only cleanup of append-only rows so the migration can go down.
        with factory.begin() as session:
            session.execute(delete(PedidoNoAsignado))
            session.execute(delete(ParadaRuta))
            session.execute(delete(Ruta))
            session.execute(delete(Optimizacion))
            session.execute(delete(Incidencia))
            session.execute(delete(Auditoria))
            session.execute(delete(Parametro))
            session.execute(delete(ParametroVersion))


def test_ruta_dorada_150_pedidos_15_vehiculos_e_idempotente(demo_factory):
    first = seed_mvp(demo_factory, PASSWORDS, FECHA, now=NOW)
    assert first.created["pedidos"] == 20 + 150
    assert first.created["vehiculos"] == 15
    assert first.created["conductores"] == 4 + 13
    assert resumen_fecha(demo_factory, FECHA) == {
        "pedidos_pendientes": 150,
        "vehiculos_activos": 15,
    }
    second = seed_mvp(demo_factory, PASSWORDS, FECHA, now=NOW + timedelta(days=5))
    assert second.created == {}
    assert second.existing["pedidos"] == 20 + 150
    assert resumen_fecha(demo_factory, FECHA)["pedidos_pendientes"] == 150


def test_ruta_infeliz_fecha_con_pedidos_ajenos(demo_factory):
    with demo_factory.begin() as session:
        cliente = Cliente(nombre="Cliente ajeno")
        session.add(cliente)
        session.flush()
        inicio = medianoche(FECHA) + timedelta(hours=10)
        session.add(
            Pedido(
                cliente_id=cliente.cliente_id,
                direccion="Calle ajena 1",
                referencia="Pedido ajeno",
                ubicacion="SRID=4326;POINT(-76.97 -12.04)",
                peso_kg=Decimal("5"),
                volumen_m3=Decimal("0.01"),
                ventana_inicio=inicio,
                ventana_fin=inicio + timedelta(hours=2),
                prioridad="ESTANDAR",
                tipo_producto="GENERAL",
            )
        )
    with pytest.raises(SeedMvpRefused, match="ajenos a la demo"):
        seed_mvp(demo_factory, PASSWORDS, FECHA, now=NOW)
    with demo_factory() as session:
        sembrados = session.scalar(
            select(func.count())
            .select_from(Pedido)
            .where(Pedido.referencia.startswith(PREFIJO_PEDIDO))
        )
    assert sembrados == 0


def test_ruta_feliz_optimizacion_real_deja_inviables_con_motivo(demo_factory):
    seed_mvp(demo_factory, PASSWORDS, FECHA, now=NOW)
    with demo_factory() as session:
        operador = UsuarioRepository(session).find_for_login(USERS[Rol.OPERADOR])
    service = OptimizacionService(demo_factory, DEPOSITO, tiempo_limite_s=2)
    aceptada = service.optimizar(
        OptimizacionSolicitud(fecha_operacion=FECHA), operador.usuario_id
    )
    detalle = service.detalle(aceptada.optimizacion_id)
    assert detalle.estado.value == "COMPLETADA"
    assert (
        detalle.resumen.pedidos_asignados + detalle.resumen.pedidos_no_asignados == 150
    )
    motivos = {n.motivo for n in detalle.no_asignados}
    assert {"EXCEDE_CAPACIDAD", "VENTANA_INVIABLE"} <= {
        getattr(m, "value", m) for m in motivos
    }


def test_ruta_infeliz_fecha_con_pedidos_de_seed_demo(demo_factory):
    """seed_demo puts orders on its first day and the next; that day is refused."""
    manana = NOW.date() + timedelta(days=1)
    with pytest.raises(SeedMvpRefused, match="seed_demo"):
        seed_mvp(demo_factory, PASSWORDS, manana, now=NOW)
    assert resumen_fecha(demo_factory, manana)["pedidos_pendientes"] < 150
