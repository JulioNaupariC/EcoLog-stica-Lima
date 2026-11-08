"""ECL-95 (ST-046): route model over PostgreSQL/PostGIS.

Migration 0016 round trip, the constraints that protect a reproducible
optimization (parameter version, final states, ECL-79 driverless routes, one
order once per run, RN-009 reasons), unrounded metrics (RNF-011) and the
jornada of a driver stop assignment for ECL-82. Data is synthetic.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import delete, inspect, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from alembic import command
from app.db.session import session_factory
from app.models import (
    Cliente,
    DriverStopAssignment,
    Incidencia,
    Optimizacion,
    ParadaRuta,
    Parametro,
    ParametroVersion,
    Pedido,
    PedidoNoAsignado,
    Ruta,
    Usuario,
    Vehiculo,
)
from app.repositories.rutas import JornadaParada, RutaRepository
from app.repositories.usuarios import UsuarioRepository
from app.services.credenciales import CredentialService

pytestmark = pytest.mark.integration

T0 = datetime(2026, 11, 9, 13, 0, tzinfo=timezone.utc)  # 08:00 in Lima
FECHA = date(2026, 11, 9)
TRAZADO = "SRID=4326;LINESTRING(-76.97 -12.06, -77.03 -12.05, -76.97 -12.06)"


@pytest.fixture
def rutas_database(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    try:
        yield factory, config
    finally:
        # 0016 refuses to downgrade while optimizations exist (operational history).
        with factory.begin() as session:
            session.execute(delete(DriverStopAssignment))
            session.execute(delete(PedidoNoAsignado))
            session.execute(delete(ParadaRuta))
            session.execute(delete(Ruta))
            session.execute(delete(Optimizacion))
            # 0017 (EN-008) refuses to downgrade while parameter versions exist.
            session.execute(delete(Parametro))
            session.execute(delete(ParametroVersion))


@pytest.fixture
def datos(rutas_database):
    factory, _ = rutas_database
    with factory.begin() as session:
        operador = (
            CredentialService(UsuarioRepository(session))
            .create("operador-rutas@example.test", "synthetic-password-1", "OPERADOR")
            .usuario_id
        )
        # EN-008: a completed run references an existing parameter version.
        session.add(
            ParametroVersion(
                version="SIMULADO-2026-11",
                vigente_desde=T0 - timedelta(days=30),
                creada_por=operador,
            )
        )
        cliente = Cliente(nombre="Cliente sintético")
        vehiculos = [
            Vehiculo(
                placa=f"RUT-{n}0{n}",
                tipo="FURGON",
                capacidad_kg=Decimal("1500"),
                capacidad_m3=Decimal("12"),
                rendimiento_km_l=Decimal("9"),
                factor_co2_kg_km=Decimal("0.29778"),
                anio_fabricacion=2022,
            )
            for n in (1, 2)
        ]
        session.add_all([cliente, *vehiculos])
        session.flush()
        pedidos = [
            Pedido(
                cliente_id=cliente.cliente_id,
                direccion=f"Av. Ficticia {n}",
                ubicacion=f"SRID=4326;POINT(-77.0{n} -12.05)",
                peso_kg=Decimal("20"),
                volumen_m3=Decimal("0.1"),
                ventana_inicio=T0,
                ventana_fin=T0 + timedelta(hours=4),
                prioridad="ESTANDAR",
                tipo_producto="GENERAL",
            )
            for n in range(1, 4)
        ]
        session.add_all(pedidos)
        session.flush()
        return {
            "operador": operador,
            "vehiculos": [v.vehiculo_id for v in vehiculos],
            "pedidos": [p.pedido_id for p in pedidos],
        }


def optimizacion(**cambios) -> Optimizacion:
    valores = {
        "solicitada_por": cambios.pop("solicitada_por"),
        "fecha_operacion": FECHA,
        "estado": "COMPLETADA",
        "solicitada_en": T0,
        "finalizada_en": T0 + timedelta(seconds=20),
        "duracion_s": 20.031,
        "parametros_version": "SIMULADO-2026-11",
        "instantanea": {"vehiculos": 2, "pedidos": 3, "matriz": "haversine-1.35"},
    }
    return Optimizacion(**{**valores, **cambios})


def ruta(optimizacion_id, vehiculo_id, **cambios) -> Ruta:
    valores = {
        "optimizacion_id": optimizacion_id,
        "fecha_operacion": FECHA,
        "vehiculo_id": vehiculo_id,
        "conductor_id": None,
        "motivo_sin_conductor": "SIN_CONDUCTOR_ELEGIBLE",
        "salida": T0,
        "regreso": T0 + timedelta(hours=2),
        "tiempo_min": 120,
        "peso_kg": Decimal("40"),
        "volumen_m3": Decimal("0.2"),
        "distancia_km": 10.0,
        "co2_kg": 20.0,
        "combustible_l": 10.0,
        "costo_soles": 0.0,
        "trazado": TRAZADO,
    }
    return Ruta(**{**valores, **cambios})


def parada(r: Ruta, pedido_id, secuencia, **cambios) -> ParadaRuta:
    return ParadaRuta(
        ruta_id=r.ruta_id,
        optimizacion_id=r.optimizacion_id,
        pedido_id=pedido_id,
        secuencia=secuencia,
        eta=T0 + timedelta(minutes=30 * secuencia),
        **cambios,
    )


def guardar(factory, *objetos):
    with factory.begin() as session:
        for objeto in objetos:
            session.add(objeto)
            session.flush()


def test_completed_run_is_persisted_reproducible_and_unrounded(rutas_database, datos):
    factory, _ = rutas_database
    run = optimizacion(
        solicitada_por=datos["operador"],
        secuencial_combustible_l=12.0,
        secuencial_co2_kg=24.0,
        cumplimiento_ventanas_pct=100.0,
    )
    guardar(factory, run)
    exacto = 10 / 6  # 1.666..., stored without rounding (RNF-011)
    r = ruta(run.optimizacion_id, datos["vehiculos"][0], combustible_l=exacto)
    guardar(factory, r)
    guardar(
        factory,
        parada(r, datos["pedidos"][0], 1),
        parada(r, datos["pedidos"][1], 2),
        PedidoNoAsignado(
            optimizacion_id=run.optimizacion_id,
            pedido_id=datos["pedidos"][2],
            motivo="JORNADA_INVIABLE",
        ),
    )
    with factory() as session:
        stored = session.get(Optimizacion, run.optimizacion_id)
        assert stored.parametros_version == "SIMULADO-2026-11"
        assert stored.instantanea["matriz"] == "haversine-1.35"
        assert stored.simulado is False
        saved = session.scalar(select(Ruta))
        assert saved.combustible_l == exacto
        assert saved.estado == "PLANIFICADA" and saved.descansos == []
        tipo, puntos, srid = session.execute(
            text(
                "SELECT GeometryType(trazado::geometry), ST_NPoints(trazado::geometry),"
                " ST_SRID(trazado::geometry) FROM ruta"
            )
        ).one()
        assert (tipo, puntos, srid) == ("LINESTRING", 3, 4326)
        paradas = session.scalars(
            select(ParadaRuta).order_by(ParadaRuta.secuencia)
        ).all()
        assert [p.estado for p in paradas] == ["PENDIENTE", "PENDIENTE"]


@pytest.mark.parametrize(
    "cambios,restriccion",
    [
        ({"parametros_version": None}, "ck_optimizacion_parametros"),
        ({"finalizada_en": None}, "ck_optimizacion_finalizada"),
        ({"estado": "EN_PROCESO"}, "ck_optimizacion_finalizada"),
        ({"estado": "FALLIDA"}, "ck_optimizacion_error"),
        ({"error": "Error seguro"}, "ck_optimizacion_error"),
        ({"estado": "PAUSADA"}, "ck_optimizacion_estado"),
        ({"finalizada_en": T0 - timedelta(seconds=1)}, "ck_optimizacion_orden_fechas"),
        ({"duracion_s": -1.0}, "ck_optimizacion_duracion"),
        ({"cumplimiento_ventanas_pct": 100.5}, "ck_optimizacion_cumplimiento"),
        ({"secuencial_co2_kg": -0.1}, "ck_optimizacion_secuencial_co2_kg"),
        ({"instantanea": []}, "ck_optimizacion_instantanea"),
    ],
)
def test_optimization_states_are_consistent(
    rutas_database, datos, cambios, restriccion
):
    factory, _ = rutas_database
    with pytest.raises(IntegrityError, match=restriccion):
        guardar(factory, optimizacion(solicitada_por=datos["operador"], **cambios))


def test_in_process_and_failed_runs(rutas_database, datos):
    factory, _ = rutas_database
    guardar(
        factory,
        optimizacion(
            solicitada_por=datos["operador"],
            estado="EN_PROCESO",
            finalizada_en=None,
            duracion_s=None,
            parametros_version=None,
        ),
        optimizacion(
            solicitada_por=datos["operador"],
            estado="FALLIDA",
            parametros_version=None,
            error="No se pudo calcular la solución",
        ),
    )
    with factory() as session:
        assert sorted(session.scalars(select(Optimizacion.estado)).all()) == [
            "EN_PROCESO",
            "FALLIDA",
        ]


@pytest.mark.parametrize(
    "cambios,restriccion",
    [
        ({"motivo_sin_conductor": None}, "ck_ruta_conductor"),
        ({"motivo_sin_conductor": "SIN_LICENCIA"}, "ck_ruta_motivo_sin_conductor"),
        ({"regreso": T0 - timedelta(minutes=1)}, "ck_ruta_horario"),
        ({"distancia_km": -0.01}, "ck_ruta_metricas"),
        ({"tiempo_min": -1}, "ck_ruta_carga"),
        ({"estado": "CERRADA"}, "ck_ruta_cerrada"),
        ({"cerrada_en": T0}, "ck_ruta_cerrada"),
        ({"descansos": {}}, "ck_ruta_descansos"),
    ],
)
def test_route_constraints(rutas_database, datos, cambios, restriccion):
    factory, _ = rutas_database
    run = optimizacion(solicitada_por=datos["operador"])
    guardar(factory, run)
    with pytest.raises(IntegrityError, match=restriccion):
        guardar(factory, ruta(run.optimizacion_id, datos["vehiculos"][0], **cambios))


def test_one_route_per_vehicle_per_run(rutas_database, datos):
    factory, _ = rutas_database
    run = optimizacion(solicitada_por=datos["operador"])
    guardar(factory, run)
    guardar(factory, ruta(run.optimizacion_id, datos["vehiculos"][0]))
    with pytest.raises(IntegrityError, match="uq_ruta_vehiculo"):
        guardar(factory, ruta(run.optimizacion_id, datos["vehiculos"][0]))


def test_an_order_is_served_once_per_run_and_stops_stay_in_their_run(
    rutas_database, datos
):
    factory, _ = rutas_database
    run, otra = (optimizacion(solicitada_por=datos["operador"]) for _ in range(2))
    guardar(factory, run, otra)
    a = ruta(run.optimizacion_id, datos["vehiculos"][0])
    b = ruta(run.optimizacion_id, datos["vehiculos"][1])
    c = ruta(otra.optimizacion_id, datos["vehiculos"][0])
    guardar(factory, a, b, c)
    guardar(factory, parada(a, datos["pedidos"][0], 1))
    # Same order in another route of the same run: rejected.
    with pytest.raises(IntegrityError, match="uq_parada_ruta_pedido"):
        guardar(factory, parada(b, datos["pedidos"][0], 1))
    # The same order in another run is a different, reproducible result.
    guardar(factory, parada(c, datos["pedidos"][0], 1))
    with pytest.raises(IntegrityError, match="uq_parada_ruta_secuencia"):
        guardar(factory, parada(a, datos["pedidos"][1], 1))
    # A stop cannot claim a route of another run (composite foreign key).
    intruso = parada(a, datos["pedidos"][2], 2)
    intruso.optimizacion_id = otra.optimizacion_id
    with pytest.raises(IntegrityError, match="fk_parada_ruta_ruta"):
        guardar(factory, intruso)
    with pytest.raises(IntegrityError, match="ck_parada_ruta_atendida"):
        guardar(factory, parada(a, datos["pedidos"][2], 2, estado="ATENDIDA"))


def test_unassigned_reason_is_from_the_catalogue(rutas_database, datos):
    factory, _ = rutas_database
    run = optimizacion(solicitada_por=datos["operador"])
    guardar(factory, run)
    with pytest.raises(IntegrityError, match="ck_pedido_no_asignado_motivo"):
        guardar(
            factory,
            PedidoNoAsignado(
                optimizacion_id=run.optimizacion_id,
                pedido_id=datos["pedidos"][0],
                motivo="TIEMPO_AGOTADO",
            ),
        )


def test_jornada_of_a_driver_stop_assignment(rutas_database, datos):
    factory, _ = rutas_database
    run = optimizacion(solicitada_por=datos["operador"])
    guardar(factory, run)
    r = ruta(run.optimizacion_id, datos["vehiculos"][0])
    guardar(factory, r)
    p = parada(r, datos["pedidos"][0], 1)
    guardar(factory, p)
    with factory() as session:
        owner = session.scalar(select(Usuario.usuario_id))
    con_ruta, sprint3 = uuid4(), uuid4()
    guardar(
        factory,
        DriverStopAssignment(
            stop_id=con_ruta, owner_id=owner, position=1, parada_ruta_id=p.parada_id
        ),
        DriverStopAssignment(stop_id=sprint3, owner_id=owner, position=2),
    )
    with factory() as session:
        repository = RutaRepository(session)
        assert repository.jornada_de_asignacion(con_ruta) == JornadaParada(
            r.ruta_id, None, FECHA
        )
        assert repository.jornada_de_asignacion(sprint3) is None
    with pytest.raises(IntegrityError, match="uq_driver_stop_parada_ruta"):
        guardar(
            factory,
            DriverStopAssignment(
                stop_id=uuid4(), owner_id=owner, position=3, parada_ruta_id=p.parada_id
            ),
        )


def test_incident_route_is_nullable_and_constrained(rutas_database):
    factory, _ = rutas_database
    columnas = {
        c["name"]: c for c in inspect(factory.kw["bind"]).get_columns("incidencia")
    }
    assert columnas["ruta_id"]["nullable"] is True
    assert Incidencia.__table__.c.ruta_id.foreign_keys


def test_migration_round_trip_and_refusal_with_history(rutas_database):
    factory, config = rutas_database
    engine = factory.kw["bind"]
    assert len(ScriptDirectory.from_config(config).get_heads()) == 1
    # Explicit target: later revisions (0017+) sit above 0016 and go down first.
    command.downgrade(config, "0015_sesion_extendida")
    with engine.connect() as connection:
        tablas = set(inspect(connection).get_table_names())
        assert not {"optimizacion", "ruta", "parada_ruta", "pedido_no_asignado"} & (
            tablas
        )
        assert "ruta_id" not in {
            c["name"] for c in inspect(connection).get_columns("incidencia")
        }
    command.upgrade(config, "0016_modelo_rutas")
    with factory.begin() as session:
        operador = (
            CredentialService(UsuarioRepository(session))
            .create("operador-mig@example.test", "synthetic-password-1", "OPERADOR")
            .usuario_id
        )
    # An in-process run needs no parameter version: 0016 is tested alone.
    guardar(
        factory,
        optimizacion(
            solicitada_por=operador,
            estado="EN_PROCESO",
            finalizada_en=None,
            parametros_version=None,
        ),
    )
    with pytest.raises(DBAPIError, match="ECL-95 optimizations"):
        command.downgrade(config, "0015_sesion_extendida")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0016_modelo_rutas"
        )
    command.upgrade(config, "head")
