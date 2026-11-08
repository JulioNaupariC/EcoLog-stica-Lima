"""ST-047 (ECL-96) over PostgreSQL/PostGIS: real optimization runs (US-006).

Selection and validation without creating runs, the engine on stored orders,
one transaction for the whole result, FALLIDA on engine failure, ECL-79 driver
assignment, RN-009 reasons, EN-008 pricing and the RNF-001 golden scenario
(150 orders, 15 vehicles). Orders, vehicles and people are synthetic.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from math import degrees
from time import perf_counter
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, text

from alembic import command
from app.core.parametros import REFERENCIA_INICIAL, UNIDADES
from app.db.session import session_factory
from app.models import (
    Auditoria,
    Cliente,
    Conductor,
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
from app.optimizacion import sinteticos
from app.optimizacion.distancias import RADIO_TIERRA_KM
from app.optimizacion.modelo import Descanso, EstadoSolucion, Metricas, Parada, Solucion
from app.optimizacion.modelo import Ruta as RutaVRP
from app.repositories.optimizaciones import OptimizacionRepository
from app.repositories.usuarios import UsuarioRepository
from app.schemas.parametro import ValorParametro, VersionCreate
from app.schemas.rutas import OptimizacionSolicitud
from app.services.credenciales import CredentialService
from app.services.optimizaciones import (
    OptimizacionFallida,
    OptimizacionService,
    SeleccionInvalida,
    medianoche,
)
from app.services.parametros import ParametroService

pytestmark = pytest.mark.integration

FECHA = date(2026, 11, 9)
AHORA = datetime(2026, 11, 8, 15, 0, tzinfo=timezone.utc)
BASE = medianoche(FECHA)


@pytest.fixture
def base_datos(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    try:
        yield factory
    finally:
        # 0016/0017 refuse to downgrade with operational history.
        with factory.begin() as session:
            session.execute(delete(PedidoNoAsignado))
            session.execute(delete(ParadaRuta))
            session.execute(delete(Ruta))
            session.execute(delete(Optimizacion))
            session.execute(delete(Parametro))
            session.execute(delete(ParametroVersion))
            session.execute(delete(Auditoria))


def _usuario(session, correo, rol):
    return (
        CredentialService(UsuarioRepository(session))
        .create(correo, "synthetic-password-1", rol)
        .usuario_id
    )


def _version(factory, admin):
    ParametroService(factory).registrar(
        VersionCreate(
            version="REF-TEST",
            vigente_desde=datetime(2026, 11, 1, 5, 0, tzinfo=timezone.utc),
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


def _vehiculos(session, cantidad):
    vehiculos = [
        Vehiculo(
            placa=f"OPT-{i:03d}",
            tipo=v.vehiculo_id.split("-")[1],
            capacidad_kg=Decimal(str(v.capacidad_kg)),
            capacidad_m3=Decimal(str(v.capacidad_m3)),
            rendimiento_km_l=Decimal(str(v.rendimiento_km_l)),
            factor_co2_kg_km=Decimal(str(v.factor_co2_kg_km)),
            anio_fabricacion=2022,
        )
        for i, v in enumerate(sinteticos.flota(cantidad))
    ]
    session.add_all(vehiculos)
    session.flush()
    return [v.vehiculo_id for v in vehiculos]


def _pedidos(session, cliente_id, problema_pedidos, fecha=FECHA):
    base = medianoche(fecha)
    pedidos = [
        Pedido(
            cliente_id=cliente_id,
            direccion=f"Calle sintética {i}",
            ubicacion=(
                None
                if p.ubicacion is None
                else f"SRID=4326;POINT({p.ubicacion.longitud} {p.ubicacion.latitud})"
            ),
            referencia=None if p.ubicacion else "Frente al parque sintético",
            peso_kg=Decimal(str(p.peso_kg)),
            volumen_m3=Decimal(str(p.volumen_m3)),
            ventana_inicio=base + timedelta(minutes=p.ventana_inicio_min),
            ventana_fin=base + timedelta(minutes=p.ventana_fin_min),
            prioridad=p.prioridad.value,
            tipo_producto="GENERAL",
        )
        for i, p in enumerate(problema_pedidos)
    ]
    session.add_all(pedidos)
    session.flush()
    return [p.pedido_id for p in pedidos]


def _conductor(session, nombre, desde, hasta):
    usuario = _usuario(session, f"{nombre.lower()}@example.test", "CONDUCTOR")
    conductor = Conductor(
        usuario_id=usuario,
        nombre=f"{nombre} Sintético",
        dni="40000001",
        licencia_numero="Q40000001",
        licencia_vigente_hasta=date(2027, 12, 31),
        experiencia_anios=5,
        telefono="+51999000111",
        disponible_desde=desde,
        disponible_hasta=hasta,
        punto_partida="Depósito Santa Anita",
    )
    session.add(conductor)
    session.flush()
    return conductor.conductor_id


@pytest.fixture
def escenario(base_datos):
    """5 feasible orders, 1 over capacity, 2 vehicles, 1 eligible driver."""
    factory = base_datos
    problema = sinteticos.escenario(6, 2, semilla=7)
    with factory.begin() as session:
        operador = _usuario(session, "operador-opt@example.test", "OPERADOR")
        admin = _usuario(session, "admin-opt@example.test", "ADMINISTRADOR")
        cliente = Cliente(nombre="Cliente sintético")
        session.add(cliente)
        session.flush()
        vehiculos = _vehiculos(session, 2)
        pedidos = _pedidos(session, cliente.cliente_id, problema.pedidos)
        conductor = _conductor(
            session, "Rosa", BASE + timedelta(hours=7), BASE + timedelta(hours=19)
        )
        # Other date: never selected automatically.
        otro = _pedidos(
            session, cliente.cliente_id, problema.pedidos[:1], FECHA + timedelta(1)
        )
    _version(factory, admin)
    return {
        "factory": factory,
        "operador": operador,
        "vehiculos": vehiculos,
        "pedidos": pedidos,
        "otro_dia": otro,
        "conductor": conductor,
        "cliente": cliente.cliente_id,
    }


def servicio(factory, **opciones):
    return OptimizacionService(
        factory,
        sinteticos.DEPOSITO,
        tiempo_limite_s=opciones.pop("tiempo_limite_s", 2),
        reloj=lambda: AHORA,
        **opciones,
    )


def _corridas(factory):
    with factory() as session:
        return session.scalar(select(func.count()).select_from(Optimizacion))


def test_automatic_selection_is_solved_stored_and_consultable(escenario):
    factory = escenario["factory"]
    service = servicio(factory)
    aceptada = service.optimizar(
        OptimizacionSolicitud(fecha_operacion=FECHA), escenario["operador"]
    )
    assert aceptada.estado.value == "COMPLETADA" and aceptada.simulado is False
    assert aceptada.solicitada_en.utcoffset() == timedelta(hours=-5)

    detalle = service.detalle(aceptada.optimizacion_id)
    assert detalle is not None and detalle.estado.value == "COMPLETADA"
    assert detalle.parametros_version == "REF-TEST" and detalle.simulado is False
    assert detalle.error is None and detalle.duracion_s is not None
    servidos = {p.pedido_id for r in detalle.rutas for p in r.paradas}
    omitidos = {n.pedido_id: n.motivo.value for n in detalle.no_asignados}
    # Every selected order is either served or explained (RN-009), never both.
    assert servidos | set(omitidos) == set(escenario["pedidos"])
    assert not servidos & set(omitidos)
    assert "EXCEDE_CAPACIDAD" in omitidos.values()
    assert "VENTANA_INVIABLE" in omitidos.values()
    assert escenario["otro_dia"][0] not in servidos | set(omitidos)

    deposito = [sinteticos.DEPOSITO.longitud, sinteticos.DEPOSITO.latitud]
    for ruta in detalle.rutas:
        assert [p.secuencia for p in ruta.paradas] == list(
            range(1, len(ruta.paradas) + 1)
        )
        for parada in ruta.paradas:
            assert parada.ventana_inicio <= parada.eta <= parada.ventana_fin
            assert parada.eta.utcoffset() == timedelta(hours=-5)
        coordenadas = [list(c) for c in ruta.trazado.coordinates]
        assert coordenadas[0] == deposito == coordenadas[-1]
        assert len(coordenadas) == len(ruta.paradas) + 2
        assert ruta.metricas.costo_soles > 0 and ruta.salida < ruta.regreso
    # ECL-79: one eligible driver, so one route has her and the rest a reason.
    conductores = [r.conductor for r in detalle.rutas]
    assert sum(c is not None for c in conductores) == 1
    con_chofer = next(r for r in detalle.rutas if r.conductor is not None)
    assert con_chofer.conductor.nombre == "Rosa Sintético"
    for ruta in detalle.rutas:
        if ruta.conductor is None:
            assert ruta.motivo_sin_conductor.value == "SIN_CONDUCTOR_ELEGIBLE"

    resumen = detalle.resumen
    assert resumen is not None and resumen.rutas == len(detalle.rutas)
    assert resumen.pedidos_asignados == len(servidos)
    assert resumen.pedidos_no_asignados == len(omitidos)
    assert resumen.cumplimiento_ventanas_pct == 100
    assert resumen.optimizada.distancia_km == pytest.approx(
        sum(r.metricas.distancia_km for r in detalle.rutas)
    )
    # EN-008: sequential cost uses the same version (gallons + maintenance).
    sec = resumen.secuencial
    esperado = sec.combustible_l / 3.785411784 * 17.50 + sec.distancia_km * 1.20
    assert sec.costo_soles == pytest.approx(esperado)
    assert resumen.ahorro_pct.distancia == pytest.approx(
        (sec.distancia_km - resumen.optimizada.distancia_km) / sec.distancia_km * 100
    )

    with factory() as session:
        run = session.get(Optimizacion, aceptada.optimizacion_id)
        assert run.instantanea["parametros"]["LITROS_POR_GALON"] == "3.785411784"
        assert len(run.instantanea["pedidos"]) == len(escenario["pedidos"])
        assert "Rosa" not in str(run.instantanea)
        # Orders keep their state: dispatch is a later step.
        estados = session.scalars(select(Pedido.estado)).all()
        assert set(estados) == {"PENDIENTE"}
        assert session.scalar(
            text("SELECT bool_and(ST_SRID(trazado::geometry) = 4326) FROM ruta")
        )

    pagina = service.listar(FECHA, 1, 20)
    assert pagina.total == 1 and pagina.simulado is False
    item = pagina.items[0]
    assert item.resumen is not None
    assert item.resumen.rutas == resumen.rutas
    assert item.resumen.pedidos_asignados == resumen.pedidos_asignados
    assert item.resumen.optimizada.costo_soles == pytest.approx(
        resumen.optimizada.costo_soles
    )


def test_explicit_selection_uses_only_the_given_ids(escenario):
    factory = escenario["factory"]
    elegidos = escenario["pedidos"][:2]
    aceptada = servicio(factory).optimizar(
        OptimizacionSolicitud(
            fecha_operacion=FECHA,
            pedido_ids=elegidos,
            vehiculo_ids=escenario["vehiculos"][:1],
        ),
        escenario["operador"],
    )
    detalle = servicio(factory).detalle(aceptada.optimizacion_id)
    vistos = {p.pedido_id for r in detalle.rutas for p in r.paradas} | {
        n.pedido_id for n in detalle.no_asignados
    }
    assert vistos == set(elegidos)
    assert {r.vehiculo.vehiculo_id for r in detalle.rutas} <= {
        escenario["vehiculos"][0]
    }


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"pedido_ids": "otro_dia"}, "pedido_ids"),
        ({"pedido_ids": "inexistente"}, "pedido_ids"),
        ({"vehiculo_ids": "inexistente"}, "vehiculo_ids"),
        ({"fecha_operacion": date(2026, 12, 25)}, "pedido_ids"),
    ],
)
def test_invalid_selection_is_rejected_without_creating_a_run(
    escenario, cambios, campo
):
    factory = escenario["factory"]
    datos = {"fecha_operacion": FECHA}
    for clave, valor in cambios.items():
        if valor == "otro_dia":
            datos[clave] = escenario["otro_dia"]
        elif valor == "inexistente":
            datos[clave] = [uuid4()]
        else:
            datos[clave] = valor
    with pytest.raises(SeleccionInvalida) as error:
        servicio(factory).optimizar(
            OptimizacionSolicitud(**datos), escenario["operador"]
        )
    assert error.value.campo == campo
    assert _corridas(factory) == 0


def test_inactive_or_missing_fleet_is_rejected(escenario):
    factory = escenario["factory"]
    with factory.begin() as session:
        session.execute(text("UPDATE vehiculo SET estado = 'INACTIVO'"))
    with pytest.raises(SeleccionInvalida) as automatica:
        servicio(factory).optimizar(
            OptimizacionSolicitud(fecha_operacion=FECHA), escenario["operador"]
        )
    with pytest.raises(SeleccionInvalida) as explicita:
        servicio(factory).optimizar(
            OptimizacionSolicitud(
                fecha_operacion=FECHA, vehiculo_ids=escenario["vehiculos"]
            ),
            escenario["operador"],
        )
    assert automatica.value.campo == explicita.value.campo == "vehiculo_ids"
    assert _corridas(factory) == 0


def test_without_parameters_in_force_no_run_is_created(escenario):
    factory = escenario["factory"]
    service = OptimizacionService(
        factory,
        sinteticos.DEPOSITO,
        reloj=lambda: datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    with pytest.raises(SeleccionInvalida) as error:
        service.optimizar(
            OptimizacionSolicitud(fecha_operacion=FECHA), escenario["operador"]
        )
    assert error.value.campo == "parametros"
    assert _corridas(factory) == 0


def _sin_solucion(problema):
    return Solucion(EstadoSolucion.SIN_SOLUCION, (), (), None, 1.0)


def _explota(problema):
    raise RuntimeError("detalle interno que no debe filtrarse")


@pytest.mark.parametrize("resolver", [_sin_solucion, _explota])
def test_engine_failure_leaves_a_failed_run_without_partial_routes(escenario, resolver):
    factory = escenario["factory"]
    service = servicio(factory, resolver=resolver)
    with pytest.raises(OptimizacionFallida) as error:
        service.optimizar(
            OptimizacionSolicitud(fecha_operacion=FECHA), escenario["operador"]
        )
    detalle = service.detalle(error.value.optimizacion_id)
    assert detalle.estado.value == "FALLIDA"
    assert detalle.error == "No se pudo calcular la solución de rutas"
    assert detalle.rutas == [] and detalle.resumen is None
    assert detalle.finalizada_en is not None
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Ruta)) == 0
    pagina = service.listar(None, 1, 20)
    assert pagina.items[0].estado.value == "FALLIDA"
    assert pagina.items[0].resumen is None


def test_listing_is_newest_first_and_paginated(escenario):
    factory = escenario["factory"]
    for hora in (1, 2, 3):
        service = OptimizacionService(
            factory,
            sinteticos.DEPOSITO,
            tiempo_limite_s=1,
            resolver=_sin_solucion,
            reloj=lambda hora=hora: AHORA + timedelta(hours=hora),
        )
        with pytest.raises(OptimizacionFallida):
            service.optimizar(
                OptimizacionSolicitud(fecha_operacion=FECHA), escenario["operador"]
            )
    service = servicio(factory)
    primera = service.listar(None, 1, 2)
    segunda = service.listar(None, 2, 2)
    assert primera.total == segunda.total == 3
    horas = [i.solicitada_en for i in primera.items + segunda.items]
    assert horas == sorted(horas, reverse=True)
    assert all(
        h.tzinfo is not None and h.utcoffset() == timedelta(hours=-5) for h in horas
    )
    assert service.listar(FECHA + timedelta(days=1), 1, 20).total == 0
    assert service.detalle(uuid4()) is None


def test_golden_150_orders_15_vehicles_end_to_end_meets_rnf001(base_datos):
    """RNF-001 smoke on real storage; EN-003 runs the 30-run P95 campaign."""
    factory = base_datos
    problema = sinteticos.escenario(150, 15, semilla=2026)
    with factory.begin() as session:
        operador = _usuario(session, "operador-golden@example.test", "OPERADOR")
        admin = _usuario(session, "admin-golden@example.test", "ADMINISTRADOR")
        cliente = Cliente(nombre="Cliente golden")
        session.add(cliente)
        session.flush()
        _vehiculos(session, 15)
        pedidos = _pedidos(session, cliente.cliente_id, problema.pedidos)
    _version(factory, admin)
    service = servicio(factory, tiempo_limite_s=5)
    inicio = perf_counter()
    aceptada = service.optimizar(OptimizacionSolicitud(fecha_operacion=FECHA), operador)
    detalle = service.detalle(aceptada.optimizacion_id)
    transcurrido = perf_counter() - inicio
    assert transcurrido <= 45
    servidos = [p.pedido_id for r in detalle.rutas for p in r.paradas]
    assert len(servidos) == len(set(servidos))
    assert len(servidos) + len(detalle.no_asignados) == len(pedidos)
    assert len(servidos) >= 140
    for ruta in detalle.rutas:
        assert ruta.peso_kg <= 1500 and ruta.paradas
        assert all(p.ventana_inicio <= p.eta <= p.ventana_fin for p in ruta.paradas)
    assert detalle.resumen.ahorro_pct.distancia is not None


@pytest.fixture
def asignacion_ecl79(escenario):
    """Use one real stored order/vehicle/driver and a deterministic engine plan."""
    return escenario


def _plan_ecl79(escenario, *, viaje=12, salida=480, pausa=None):
    factory = escenario["factory"]
    # Same Haversine/speed/detour as ST-044. Aim half a minute below the
    # desired integer so rounding remains stable across platforms.
    distancia = (viaje - 0.5) / 60 * 20 / 1.35
    latitud = sinteticos.DEPOSITO.latitud + degrees(distancia / RADIO_TIERRA_KM)
    with factory.begin() as session:
        pedido = session.get(Pedido, escenario["pedidos"][0])
        pedido.ubicacion = f"SRID=4326;POINT({sinteticos.DEPOSITO.longitud} {latitud})"
        pedido.ventana_inicio = BASE + timedelta(minutes=salida)
        pedido.ventana_fin = BASE + timedelta(days=2)
        driver = session.get(Conductor, escenario["conductor"])
        driver.disponible_desde = BASE
        driver.disponible_hasta = BASE + timedelta(days=2)
        driver.licencia_vigente_hasta = FECHA
    eta = salida + viaje
    descansos = () if pausa is None else (Descanso(eta + 5, pausa),)
    regreso = eta + 5 + (pausa or 0) + viaje

    def resolver(problema):
        ruta = RutaVRP(
            vehiculo_id=problema.vehiculos[0].vehiculo_id,
            paradas=(Parada(1, problema.pedidos[0].pedido_id, eta),),
            salida_min=salida,
            regreso_min=regreso,
            peso_kg=1,
            volumen_m3=1,
            metricas=Metricas(distancia * 2, 1, 1),
            descansos=descansos,
        )
        return Solucion(EstadoSolucion.COMPLETADA, (ruta,), (), None, 0.01)

    solicitud = OptimizacionSolicitud(
        fecha_operacion=FECHA,
        pedido_ids=[escenario["pedidos"][0]],
        vehiculo_ids=[escenario["vehiculos"][0]],
    )
    return servicio(factory, resolver=resolver), solicitud


@pytest.mark.parametrize(
    "viaje,pausa,elegible",
    [
        (120, None, True),
        (121, None, False),
        (240, 60, True),
        (241, 60, False),
        (240, 59, False),
    ],
    ids=[
        "4h-sin-pausa",
        "4h2min-sin-pausa",
        "8h-descanso-exacto",
        "8h2min",
        "descanso-59min",
    ],
)
def test_ECL79_F1_F2_asignacion_persistida_y_solucion_conservada(
    asignacion_ecl79, viaje, pausa, elegible
):
    datos = asignacion_ecl79
    service, solicitud = _plan_ecl79(datos, viaje=viaje, pausa=pausa)
    aceptada = service.optimizar(solicitud, datos["operador"])
    assert aceptada.estado.value == "COMPLETADA"
    detalle = service.detalle(aceptada.optimizacion_id)
    [ruta] = detalle.rutas
    assert len(ruta.paradas) == 1
    assert not detalle.no_asignados
    if elegible:
        assert ruta.conductor.conductor_id == datos["conductor"]
        assert ruta.motivo_sin_conductor is None
    else:
        assert ruta.conductor is None
        assert ruta.motivo_sin_conductor.value == "JORNADA_INVIABLE"
    with datos["factory"]() as session:
        almacenada = session.scalar(select(Ruta))
        assert almacenada.conductor_id == (datos["conductor"] if elegible else None)
        assert session.scalar(select(func.count()).select_from(ParadaRuta)) == 1


@pytest.mark.parametrize("salida,elegible", [(23 * 60, True), (23 * 60 + 50, False)])
def test_ECL79_D3_licencia_toda_conduccion_cruce_medianoche(
    asignacion_ecl79, salida, elegible
):
    datos = asignacion_ecl79
    service, solicitud = _plan_ecl79(datos, salida=salida)
    aceptada = service.optimizar(solicitud, datos["operador"])
    [ruta] = service.detalle(aceptada.optimizacion_id).rutas
    assert (ruta.conductor is not None) is elegible
    if not elegible:
        assert ruta.motivo_sin_conductor.value == "LICENCIA_VENCIDA"
    # The final day licence passes the coarse date filter in both cases;
    # the final route's driving timeline decides whether assignment is possible.
    with datos["factory"]() as session:
        assert OptimizacionRepository(session).conductores_candidatos()


@pytest.mark.parametrize(
    "cambio",
    [
        "conductor-inactivo",
        "cuenta-inactiva",
        "otro-rol",
        "sin-disponibilidad",
        "licencia-vencida",
    ],
)
def test_ECL79_candidatos_reales_excluyen_perfiles_no_autorizados(
    asignacion_ecl79, cambio
):
    datos = asignacion_ecl79
    service, solicitud = _plan_ecl79(datos)
    with datos["factory"].begin() as session:
        chofer = session.get(Conductor, datos["conductor"])
        cuenta = session.get(Usuario, chofer.usuario_id)
        if cambio == "conductor-inactivo":
            chofer.estado = "INACTIVO"
        elif cambio == "cuenta-inactiva":
            cuenta.estado = "INACTIVO"
        elif cambio == "otro-rol":
            cuenta.rol = "OPERADOR"
        elif cambio == "sin-disponibilidad":
            chofer.disponible_desde = chofer.disponible_hasta = None
        else:
            chofer.licencia_vigente_hasta = FECHA - timedelta(days=1)
    aceptada = service.optimizar(solicitud, datos["operador"])
    [ruta] = service.detalle(aceptada.optimizacion_id).rutas
    assert ruta.conductor is None
    assert ruta.motivo_sin_conductor.value == (
        "LICENCIA_VENCIDA"
        if cambio == "licencia-vencida"
        else "DISPONIBILIDAD_INSUFICIENTE"
        if cambio == "sin-disponibilidad"
        else "SIN_CONDUCTOR_ELEGIBLE"
    )


@pytest.mark.parametrize(
    "borde,elegible", [("exacto", True), ("inicio+1min", False), ("fin-1min", False)]
)
def test_ECL79_disponibilidad_se_comprueba_para_la_ruta_completa(
    asignacion_ecl79, borde, elegible
):
    datos = asignacion_ecl79
    service, solicitud = _plan_ecl79(datos)
    with datos["factory"].begin() as session:
        chofer = session.get(Conductor, datos["conductor"])
        chofer.disponible_desde = BASE + timedelta(
            minutes=480 + (borde == "inicio+1min")
        )
        chofer.disponible_hasta = BASE + timedelta(minutes=509 - (borde == "fin-1min"))
    aceptada = service.optimizar(solicitud, datos["operador"])
    [ruta] = service.detalle(aceptada.optimizacion_id).rutas
    assert (ruta.conductor is not None) is elegible


def test_ECL79_migracion_0018_round_trip_y_una_cabeza(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    with engine.connect() as connection:
        definition = connection.scalar(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname='ck_ruta_motivo_sin_conductor'"
            )
        )
        assert "LICENCIA_VENCIDA" in definition
        assert "DISPONIBILIDAD_INSUFICIENTE" in definition
        assert "JORNADA_INVIABLE" in definition
    command.downgrade(config, "0017_parametros_versionados")
    with engine.connect() as connection:
        definition = connection.scalar(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname='ck_ruta_motivo_sin_conductor'"
            )
        )
        assert "LICENCIA_VENCIDA" not in definition
    command.upgrade(config, "head")
    command.check(config)
    from alembic.script import ScriptDirectory

    assert ScriptDirectory.from_config(config).get_heads() == [
        "0018_motivos_elegibilidad"
    ]


def test_ECL79_downgrade_no_borra_motivos_operativos(
    asignacion_ecl79, migration_database
):
    datos = asignacion_ecl79
    service, solicitud = _plan_ecl79(datos, salida=23 * 60 + 50)
    ack = service.optimizar(solicitud, datos["operador"])
    _, config = migration_database
    with pytest.raises(RuntimeError, match="ECL-79 reasons require manual treatment"):
        command.downgrade(config, "0017_parametros_versionados")
    [ruta] = service.detalle(ack.optimizacion_id).rutas
    assert ruta.motivo_sin_conductor.value == "LICENCIA_VENCIDA"
