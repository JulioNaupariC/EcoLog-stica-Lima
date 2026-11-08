"""ECL-119 over PostgreSQL/PostGIS: stop outcomes, closure and US-009 aggregate.

Real optimizations produce the routes; the Operator records outcomes and
closes them; the dashboard adds only routes closed in the period (BDD US-009
D01, D05, D06 and D07). Data is synthetic.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import DBAPIError

from alembic import command
from app.core.parametros import REFERENCIA_INICIAL, UNIDADES
from app.db.session import session_factory
from app.models import (
    Auditoria,
    Cliente,
    Optimizacion,
    ParadaRuta,
    Parametro,
    ParametroVersion,
    Pedido,
    PedidoNoAsignado,
    Ruta,
    Vehiculo,
)
from app.optimizacion import sinteticos
from app.repositories.usuarios import UsuarioRepository
from app.schemas.parametro import ValorParametro, VersionCreate
from app.schemas.rutas import OptimizacionSolicitud, ResultadoParadaSolicitud
from app.services.cierre_rutas import (
    CierreConflicto,
    CierreRutaService,
    ResultadoInvalido,
)
from app.services.credenciales import CredentialService
from app.services.optimizaciones import OptimizacionService, medianoche
from app.services.parametros import ParametroService

pytestmark = pytest.mark.integration

FECHA = date(2026, 11, 16)
BASE = medianoche(FECHA)
SOLICITUD = BASE - timedelta(hours=12)
FIN_JORNADA = BASE + timedelta(hours=20)


@pytest.fixture
def base(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    with factory.begin() as session:
        operador = _usuario(session, "operador-cierre@example.test", "OPERADOR")
        admin = _usuario(session, "admin-cierre@example.test", "ADMINISTRADOR")
        cliente = Cliente(nombre="Cliente sintético cierre")
        session.add(cliente)
        session.flush()
        vehiculos = [
            Vehiculo(
                placa=f"CIE-{i:03d}",
                tipo="CAMIONETA",
                capacidad_kg=Decimal("800"),
                capacidad_m3=Decimal("4"),
                rendimiento_km_l=Decimal("11"),
                factor_co2_kg_km=Decimal("0.24364"),
                anio_fabricacion=2022,
            )
            for i in range(3)
        ]
        session.add_all(vehiculos)
        session.flush()
        ids = {
            "operador": operador,
            "cliente": cliente.cliente_id,
            "vehiculos": [v.vehiculo_id for v in vehiculos],
        }
    ParametroService(factory).registrar(
        VersionCreate(
            version="REF-CIERRE",
            vigente_desde=datetime(2026, 11, 1, 5, tzinfo=timezone.utc),
            valores=[
                ValorParametro(
                    codigo=v.codigo,
                    valor=v.valor,
                    unidad=UNIDADES[v.codigo],
                    fuente=v.fuente,
                )
                for v in REFERENCIA_INICIAL
            ],
        ),
        admin,
    )
    try:
        yield factory, config, ids
    finally:
        with factory.begin() as session:
            for modelo in (PedidoNoAsignado, ParadaRuta, Ruta, Optimizacion):
                session.execute(delete(modelo))
            for modelo in (Parametro, ParametroVersion, Auditoria):
                session.execute(delete(modelo))


def _usuario(session, correo, rol):
    return (
        CredentialService(UsuarioRepository(session))
        .create(correo, "synthetic-password-1", rol)
        .usuario_id
    )


def _pedidos(factory, cliente_id, ventanas):
    """Orders near the depot with the given (start, end) hours."""
    with factory.begin() as session:
        pedidos = [
            Pedido(
                cliente_id=cliente_id,
                direccion=f"Calle sintética {i}",
                ubicacion=f"SRID=4326;POINT({-76.968 + 0.004 * (i + 1)} -12.04)",
                peso_kg=Decimal("20"),
                volumen_m3=Decimal("0.1"),
                ventana_inicio=BASE + timedelta(hours=inicio),
                ventana_fin=BASE + timedelta(hours=fin),
                prioridad="ESTANDAR",
                tipo_producto="GENERAL",
            )
            for i, (inicio, fin) in enumerate(ventanas)
        ]
        session.add_all(pedidos)
        session.flush()
        return [p.pedido_id for p in pedidos]


def _ruta_optimizada(factory, ids, pedidos, vehiculo=0):
    """One real optimization with one vehicle: returns its single route."""
    run = OptimizacionService(
        factory, sinteticos.DEPOSITO, tiempo_limite_s=1, reloj=lambda: SOLICITUD
    ).optimizar(
        OptimizacionSolicitud(
            fecha_operacion=FECHA,
            pedido_ids=pedidos,
            vehiculo_ids=[ids["vehiculos"][vehiculo]],
        ),
        ids["operador"],
    )
    with factory() as session:
        ruta = session.scalars(
            select(Ruta).where(Ruta.optimizacion_id == run.optimizacion_id)
        ).one()
        paradas = session.scalars(
            select(ParadaRuta)
            .where(ParadaRuta.ruta_id == ruta.ruta_id)
            .order_by(ParadaRuta.secuencia)
        ).all()
    return ruta, paradas


def _servir(factory, ruta, paradas, fallidas=()):
    """ETA-based real times: served inside the window unless listed as failed."""
    service = CierreRutaService(factory, reloj=lambda: FIN_JORNADA)
    for p in paradas:
        estado = "NO_ATENDIDA" if p.pedido_id in fallidas else "ATENDIDA"
        service.registrar_parada(
            ruta.ruta_id,
            p.parada_id,
            ResultadoParadaSolicitud(
                estado=estado, atendida_en=p.eta if estado == "ATENDIDA" else None
            ),
        )


def _cierres(factory):
    with factory() as session:
        return session.scalar(
            select(func.count())
            .select_from(Auditoria)
            .where(Auditoria.accion == "RUTA_CERRADA")
        )


def test_full_flow_from_optimization_to_the_dashboard(base):
    factory, _, ids = base
    pedidos = _pedidos(factory, ids["cliente"], [(9, 12), (9, 12), (10, 13)])
    ruta, paradas = _ruta_optimizada(factory, ids, pedidos)
    assert ruta.estado == "PLANIFICADA" and ruta.secuencial_distancia_km > 0
    assert ruta.secuencial_costo_soles > 0
    service = CierreRutaService(factory, reloj=lambda: FIN_JORNADA)

    # D05: never closed with pending stops, nor by a reached ETA.
    with pytest.raises(CierreConflicto, match="Faltan 3 paradas"):
        service.cerrar(ruta.ruta_id, ids["operador"])

    _servir(factory, ruta, paradas, fallidas={paradas[-1].pedido_id})
    with factory() as session:
        assert session.get(Ruta, ruta.ruta_id).estado == "EN_CURSO"
    # A final outcome is never overwritten.
    with pytest.raises(CierreConflicto):
        service.registrar_parada(
            ruta.ruta_id,
            paradas[0].parada_id,
            ResultadoParadaSolicitud(estado="NO_ATENDIDA"),
        )

    cierre = service.cerrar(ruta.ruta_id, ids["operador"])
    assert cierre.estado.value == "CERRADA" and cierre.cerrada_en == FIN_JORNADA
    assert (cierre.paradas_atendidas, cierre.paradas_no_atendidas) == (2, 1)
    # Repeating the closure returns the stored one, with a single audit row.
    otra = CierreRutaService(factory, reloj=lambda: FIN_JORNADA + timedelta(hours=1))
    assert otra.cerrar(ruta.ruta_id, ids["operador"]).cerrada_en == FIN_JORNADA
    assert _cierres(factory) == 1
    with factory() as session:
        detalle = session.scalars(
            select(Auditoria.detalle).where(Auditoria.accion == "RUTA_CERRADA")
        ).one()
        assert detalle == {"paradas_atendidas": 2, "paradas_no_atendidas": 1}
        assert session.get(Ruta, ruta.ruta_id).cerrada_en == FIN_JORNADA

    datos = service.indicadores(FECHA, FECHA)
    assert datos.con_datos and datos.rutas_cerradas == 1 and not datos.simulado
    assert datos.distancia_km == pytest.approx(ruta.distancia_km)
    assert datos.costo_soles == pytest.approx(ruta.costo_soles)
    ahorro = datos.ahorro_vs_secuencial
    assert ahorro.distancia_km == pytest.approx(
        ruta.secuencial_distancia_km - ruta.distancia_km
    )
    assert ahorro.pct == pytest.approx(
        (ruta.secuencial_distancia_km - ruta.distancia_km)
        / ruta.secuencial_distancia_km
        * 100
    )
    # Two served inside their windows out of three terminal stops.
    assert datos.cumplimiento_ventanas_pct == pytest.approx(200 / 3)
    assert datos.parametros_versiones == ["REF-CIERRE"]
    # A closed route cannot get new outcomes.
    with pytest.raises(CierreConflicto, match="cerrada"):
        service.registrar_parada(
            ruta.ruta_id,
            paradas[0].parada_id,
            ResultadoParadaSolicitud(estado="NO_ATENDIDA"),
        )


def test_late_service_counts_as_out_of_window(base):
    factory, _, ids = base
    pedidos = _pedidos(factory, ids["cliente"], [(9, 10)])
    ruta, paradas = _ruta_optimizada(factory, ids, pedidos)
    service = CierreRutaService(factory, reloj=lambda: FIN_JORNADA)
    service.registrar_parada(
        ruta.ruta_id,
        paradas[0].parada_id,
        ResultadoParadaSolicitud(
            estado="ATENDIDA", atendida_en=BASE + timedelta(hours=11)
        ),
    )
    service.cerrar(ruta.ruta_id, ids["operador"])
    assert service.indicadores(FECHA, FECHA).cumplimiento_ventanas_pct == 0


def test_period_limits_use_the_closing_instant_in_lima(base):
    """D07: closures at 00:00 of the first day, the last instant of the last day
    and 00:00 of the next one; only the first two belong to the period."""
    factory, _, ids = base
    instantes = [
        BASE,
        medianoche(FECHA + timedelta(days=1)) - timedelta(microseconds=1),
        medianoche(FECHA + timedelta(days=1)),
    ]
    for i, instante in enumerate(instantes):
        pedidos = _pedidos(factory, ids["cliente"], [(9, 12)])
        ruta, paradas = _ruta_optimizada(factory, ids, pedidos, vehiculo=i)
        _servir(factory, ruta, paradas)
        CierreRutaService(factory, reloj=lambda instante=instante: instante).cerrar(
            ruta.ruta_id, ids["operador"]
        )
    service = CierreRutaService(factory)
    assert service.indicadores(FECHA, FECHA).rutas_cerradas == 2
    siguiente = FECHA + timedelta(days=1)
    assert service.indicadores(siguiente, siguiente).rutas_cerradas == 1
    assert service.indicadores(FECHA, siguiente).rutas_cerradas == 3
    # An optimization COMPLETADA alone adds nothing; neither does another period.
    vacio = service.indicadores(date(2026, 10, 1), date(2026, 10, 31))
    assert not vacio.con_datos and vacio.distancia_km is None


def test_service_time_outside_the_day_is_rejected(base):
    factory, _, ids = base
    pedidos = _pedidos(factory, ids["cliente"], [(9, 12)])
    ruta, paradas = _ruta_optimizada(factory, ids, pedidos)
    service = CierreRutaService(factory, reloj=lambda: FIN_JORNADA)
    with pytest.raises(ResultadoInvalido):
        service.registrar_parada(
            ruta.ruta_id,
            paradas[0].parada_id,
            ResultadoParadaSolicitud(
                estado="ATENDIDA", atendida_en=BASE - timedelta(minutes=1)
            ),
        )


def test_routes_stored_before_0018_cannot_close(base):
    factory, _, ids = base
    pedidos = _pedidos(factory, ids["cliente"], [(9, 12)])
    ruta, paradas = _ruta_optimizada(factory, ids, pedidos)
    with factory.begin() as session:
        session.execute(
            text(
                "UPDATE ruta SET secuencial_distancia_km = NULL, "
                "secuencial_co2_kg = NULL, secuencial_combustible_l = NULL, "
                "secuencial_costo_soles = NULL"
            )
        )
    _servir(factory, ruta, paradas)
    with pytest.raises(CierreConflicto, match="referencia secuencial"):
        CierreRutaService(factory, reloj=lambda: FIN_JORNADA).cerrar(
            ruta.ruta_id, ids["operador"]
        )


def test_downgrade_refuses_with_closed_routes(base):
    factory, config, ids = base
    pedidos = _pedidos(factory, ids["cliente"], [(9, 12)])
    ruta, paradas = _ruta_optimizada(factory, ids, pedidos)
    _servir(factory, ruta, paradas)
    CierreRutaService(factory, reloj=lambda: FIN_JORNADA).cerrar(
        ruta.ruta_id, ids["operador"]
    )
    with pytest.raises(DBAPIError, match="ECL-119 route closures"):
        command.downgrade(config, "0017_parametros_versionados")
    with factory() as session:
        assert session.scalar(text("SELECT version_num FROM alembic_version")) == (
            ScriptDirectory.from_config(config).get_current_head()
        )
