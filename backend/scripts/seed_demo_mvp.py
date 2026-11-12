"""ECL-105: datos de la demostración final del MVP (Sprint 4).

Uso (desde ``backend/``, con la base ``*_demo`` migrada a ``head``)::

    python -m scripts.seed_demo_mvp --fecha 2026-11-20

Completa el conjunto de ``seed_demo`` (usuarios de los cinco roles, clientes,
5 vehículos, 4 conductores, parámetros EN-008 e incidencias) con el escenario
de RNF-001 para un día de operación:

* **150 pedidos PENDIENTE** en total para el día indicado, en San Juan de
  Lurigancho, El Agustino, Santa Anita y Ate. Incluye 2 inviables a
  propósito (uno excede la capacidad de toda la flota y otro tiene la ventana
  antes de la jornada), para mostrar «no asignado con motivo» (US-006, E3).
* **15 vehículos ACTIVO**: los 5 de ``seed_demo`` y 10 más.
* **15 conductores elegibles**: los 2 elegibles de ``seed_demo`` y 13 más. Los
  2 no elegibles de ``seed_demo`` (licencia vencida y sin disponibilidad) se
  conservan para mostrar RN-005.

Los pedidos salen de ``app.optimizacion.sinteticos`` (semilla fija), el mismo
generador del benchmark de RNF-001 (ECL-21): puntos aleatorios dentro de cajas
aproximadas de cada distrito. Son datos **ficticios**, no de DistriRápido.

Mismas protecciones que ``seed_demo``: solo bases cuyo nombre termina en
``_demo``, nunca con ``APP_ENV=production``, y contraseñas leídas de
``SEED_DEMO_PASSWORD_<ROL>``, sin escribirse ni imprimirse. Los 13 conductores
nuevos usan la contraseña de ``SEED_DEMO_PASSWORD_CONDUCTOR``.

Es idempotente (por referencia del pedido, placa y DNI). Si la fecha ya tiene
otros pedidos PENDIENTE (``seed_demo`` deja algunos en el día de su primera
ejecución y en el siguiente), siembra solo los que faltan para llegar a 150, que
es lo que admite el optimizador por fecha. Así la demo puede ser **hoy**, con el
itinerario y las incidencias de ``seed_demo`` en la misma jornada. Se niega si la
fecha está en el pasado o si ya tiene más de 50 pedidos ajenos.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.rbac import Rol
from app.db.session import build_engine, session_factory
from app.models.cliente import Cliente
from app.models.conductor import Conductor
from app.models.pedido import Pedido
from app.models.vehiculo import Vehiculo
from app.optimizacion import sinteticos
from app.optimizacion.modelo import PedidoVRP
from app.repositories.usuarios import UsuarioRepository
from app.schemas.conductor import ConductorCreate
from app.schemas.pedido import PedidoCreate
from app.schemas.vehiculo import VehicleCreate
from app.services.conductores import ConductorService
from app.services.optimizaciones import medianoche
from app.services.pedidos import PedidoService
from app.services.vehiculos import VehicleDuplicatePlate, VehiculoService
from scripts import seed_demo as base

TOTAL_PEDIDOS = 150
MAX_AJENOS = 50  # other PENDIENTE orders the date may already hold
SEMILLA = 105  # fixed: the same scenario on every run and every PC
PREFIJO_PEDIDO = "Pedido MVP "
PRODUCTOS = ("Abarrotes", "Farmacia", "Limpieza", "Bebidas", "Ferretería")

# (placa, tipo); capacity, efficiency and emission factor come from
# sinteticos.FLOTA, the typical values of each type used by the benchmark.
VEHICULOS: tuple[tuple[str, str], ...] = (
    ("MVP-001", "FURGON"),
    ("MVP-002", "CAMIONETA"),
    ("MVP-003", "FURGON"),
    ("MVP-004", "CAMIONETA"),
    ("MVP-005", "FURGON"),
    ("MVP-006", "CAMIONETA"),
    ("MVP-007", "FURGON"),
    ("MVP-008", "CAMIONETA"),
    ("MVP-009", "CAMIONETA"),
    ("MVP-010", "MOTO"),
)
PRIMER_CONDUCTOR = 5  # seed_demo already has drivers 1-4
TOTAL_CONDUCTORES_NUEVOS = 13


class SeedMvpRefused(RuntimeError):
    """The requested day cannot hold the MVP scenario."""


@dataclass(frozen=True)
class PedidoDemo:
    referencia: str
    distrito: str
    vrp: PedidoVRP


def distrito_de(latitud: float, longitud: float) -> str:
    """District box of a synthetic point; the generator only draws inside them."""
    for nombre, (lat_min, lat_max, lon_min, lon_max) in sinteticos.DISTRITOS.items():
        if lat_min <= latitud <= lat_max and lon_min <= longitud <= lon_max:
            return nombre
    raise ValueError("Punto fuera de los cuatro distritos piloto")


def pedidos_demo(total: int | None = None) -> tuple[PedidoDemo, ...]:
    """``total`` demo orders (150 by default), the last 2 infeasible on purpose."""
    problema = sinteticos.escenario(
        total or TOTAL_PEDIDOS, len(VEHICULOS) + len(base.VEHICLES), semilla=SEMILLA
    )
    return tuple(
        PedidoDemo(
            referencia=f"{PREFIJO_PEDIDO}{i:03d}",
            distrito=distrito_de(p.ubicacion.latitud, p.ubicacion.longitud),
            vrp=p,
        )
        for i, p in enumerate(problema.pedidos, start=1)
    )


def conductores_demo() -> tuple[base.DemoDriver, ...]:
    return tuple(
        base.DemoDriver(
            f"Conductor Demo MVP {n:02d}",
            f"900000{n:02d}",
            f"Q-DEMO-{n:02d}",
            f"conductor{n}.demo@ecologistica.example",
            f"+519000000{n:02d}",
        )
        for n in range(PRIMER_CONDUCTOR, PRIMER_CONDUCTOR + TOTAL_CONDUCTORES_NUEVOS)
    )


def parse_fecha(texto: str, hoy: date) -> date:
    try:
        fecha = date.fromisoformat(texto)
    except ValueError:
        raise SeedMvpRefused("La fecha debe tener el formato AAAA-MM-DD.") from None
    if fecha < hoy:
        raise SeedMvpRefused("La fecha de operación no puede estar en el pasado.")
    return fecha


# --- Siembra ---------------------------------------------------------------


def _clientes(
    factory: sessionmaker[Session], summary: base.SeedSummary
) -> dict[str, UUID]:
    """One fictitious client per district."""
    ids: dict[str, UUID] = {}
    for distrito in sorted(sinteticos.DISTRITOS):
        nombre = f"Cliente Demo MVP {distrito}"
        with factory.begin() as session:
            cliente_id = session.scalar(
                select(Cliente.cliente_id).where(Cliente.nombre == nombre)
            )
            if cliente_id is None:
                cliente = Cliente(nombre=nombre)
                session.add(cliente)
                session.flush()
                cliente_id = cliente.cliente_id
                summary.count("clientes", created=True)
            else:
                summary.count("clientes", created=False)
        ids[distrito] = cliente_id
    return ids


def _vehiculos(factory: sessionmaker[Session], summary: base.SeedSummary) -> None:
    service = VehiculoService(factory)
    for placa, tipo in VEHICULOS:
        kg, m3, rendimiento, factor = sinteticos.FLOTA[tipo]
        try:
            service.create(
                VehicleCreate(
                    placa=placa,
                    tipo=tipo,
                    capacidad_kg=Decimal(str(kg)),
                    capacidad_m3=Decimal(str(m3)),
                    rendimiento_km_l=Decimal(str(rendimiento)),
                    factor_co2_kg_km=Decimal(str(factor)),
                    anio_fabricacion=2023,
                )
            )
            summary.count("vehiculos", created=True)
        except VehicleDuplicatePlate:
            summary.count("vehiculos", created=False)


def _conductores(
    factory: sessionmaker[Session],
    password: str,
    actor_id: UUID,
    now: datetime,
    fecha: date,
    summary: base.SeedSummary,
) -> None:
    service = ConductorService(factory)
    inicio = now - timedelta(hours=1)
    fin = max(inicio + timedelta(days=30), medianoche(fecha) + timedelta(days=2))
    for driver in conductores_demo():
        with factory() as session:
            existe = session.scalar(
                select(Conductor.conductor_id).where(Conductor.dni == driver.dni)
            )
        if existe is not None:
            summary.count("conductores", created=False)
            continue
        service.create(
            ConductorCreate(
                nombre=driver.nombre,
                dni=driver.dni,
                licencia_numero=driver.licencia,
                licencia_vigente_hasta=date(fecha.year + 3, 12, 31),
                experiencia_anios=3,
                telefono=driver.telefono,
                punto_partida="Centro de distribución ficticio, Santa Anita",
                disponible_desde=inicio,
                disponible_hasta=fin,
                email=driver.email,
                password=password,
            ),
            actor_id,
        )
        summary.count("conductores", created=True)


def _otros_pendientes(factory: sessionmaker[Session], fecha: date) -> int:
    inicio = medianoche(fecha)
    with factory() as session:
        return session.scalar(
            select(func.count())
            .select_from(Pedido)
            .where(
                Pedido.estado == "PENDIENTE",
                Pedido.ventana_inicio >= inicio,
                Pedido.ventana_inicio < inicio + timedelta(days=1),
                Pedido.referencia.is_(None)
                | ~Pedido.referencia.startswith(PREFIJO_PEDIDO),
            )
        )


def _pedidos(
    factory: sessionmaker[Session],
    clientes: Mapping[str, UUID],
    fecha: date,
    summary: base.SeedSummary,
    total: int,
) -> None:
    service = PedidoService(factory)
    inicio_dia = medianoche(fecha)
    with factory() as session:
        existentes = set(
            session.scalars(
                select(Pedido.referencia).where(
                    Pedido.referencia.startswith(PREFIJO_PEDIDO)
                )
            )
        )
    for i, pedido in enumerate(pedidos_demo(total)):
        if pedido.referencia in existentes:
            summary.count("pedidos", created=False)
            continue
        p = pedido.vrp
        service.create(
            PedidoCreate(
                cliente_id=clientes[pedido.distrito],
                direccion=f"Calle ficticia {100 + i * 3}, {pedido.distrito}",
                referencia=pedido.referencia,
                latitud=p.ubicacion.latitud,
                longitud=p.ubicacion.longitud,
                peso_kg=Decimal(str(p.peso_kg)),
                volumen_m3=Decimal(str(p.volumen_m3)),
                ventana_inicio=inicio_dia + timedelta(minutes=p.ventana_inicio_min),
                ventana_fin=inicio_dia + timedelta(minutes=p.ventana_fin_min),
                prioridad=p.prioridad.value,
                tipo_producto=PRODUCTOS[i % len(PRODUCTOS)],
            )
        )
        summary.count("pedidos", created=True)


def seed_mvp(
    factory: sessionmaker[Session],
    passwords: Mapping[Rol, str],
    fecha: date,
    *,
    now: datetime | None = None,
) -> base.SeedSummary:
    """Run seed_demo, then add the MVP scenario for ``fecha``; safe to repeat."""
    now = now or datetime.now(base.LIMA)
    summary = base.seed(factory, passwords, now=now)
    # seed_demo leaves some PENDIENTE orders on the day of its first run and the
    # next (its driver's stops and incidents belong to that day too). The demo
    # fills the date up to 150 so the optimizer sees exactly RNF-001's load.
    otros = _otros_pendientes(factory, fecha)
    with factory() as session:
        ya_sembrados = session.scalar(
            select(func.count())
            .select_from(Pedido)
            .where(Pedido.referencia.startswith(PREFIJO_PEDIDO))
        )
    total = ya_sembrados or TOTAL_PEDIDOS - otros
    if otros + total > TOTAL_PEDIDOS or total < TOTAL_PEDIDOS - MAX_AJENOS:
        raise SeedMvpRefused(
            f"El {fecha.isoformat()} ya tiene {otros} pedidos PENDIENTE ajenos a "
            "la demo; elige otra fecha para no superar los 150 del optimizador."
        )
    with factory() as session:
        admin = UsuarioRepository(session).find_for_login(base.USERS[Rol.ADMINISTRADOR])
    if admin is None:  # base.seed always creates it; guard against a broken base
        raise SeedMvpRefused("No existe la cuenta de administrador de la demo.")
    clientes = _clientes(factory, summary)
    _vehiculos(factory, summary)
    _conductores(
        factory, passwords[Rol.CONDUCTOR], admin.usuario_id, now, fecha, summary
    )
    _pedidos(factory, clientes, fecha, summary, total)
    return summary


def resumen_fecha(factory: sessionmaker[Session], fecha: date) -> dict[str, int]:
    """What the optimizer will see for ``fecha``."""
    inicio = medianoche(fecha)
    with factory() as session:
        pendientes = session.scalar(
            select(func.count())
            .select_from(Pedido)
            .where(
                Pedido.estado == "PENDIENTE",
                Pedido.ventana_inicio >= inicio,
                Pedido.ventana_inicio < inicio + timedelta(days=1),
            )
        )
        activos = session.scalar(
            select(func.count())
            .select_from(Vehiculo)
            .where(Vehiculo.estado == "ACTIVO")
        )
    return {"pedidos_pendientes": pendientes or 0, "vehiculos_activos": activos or 0}


def main(
    argv: Sequence[str] | None = None, environ: Mapping[str, str] = os.environ
) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--fecha", required=True, help="Día de operación de la demo (AAAA-MM-DD)"
    )
    args = parser.parse_args(argv)
    settings = Settings()
    database_url = (
        settings.database_url.get_secret_value() if settings.database_url else None
    )
    try:
        base.ensure_demo_target(database_url, environ.get("APP_ENV", settings.app_env))
        passwords = base.read_passwords(environ)
        fecha = parse_fecha(args.fecha, datetime.now(base.LIMA).date())
    except (base.SeedRefused, SeedMvpRefused) as error:
        print(f"seed_demo_mvp: {error}", file=sys.stderr)
        return 2
    engine = build_engine(settings)
    try:
        factory = session_factory(engine)
        try:
            summary = seed_mvp(factory, passwords, fecha)
        except SeedMvpRefused as error:
            print(f"seed_demo_mvp: {error}", file=sys.stderr)
            return 2
        totales = resumen_fecha(factory, fecha)
    finally:
        engine.dispose()
    for kind in ("usuarios", "clientes", "vehiculos", "conductores", "pedidos"):
        print(
            f"{kind}: {summary.created.get(kind, 0)} creados, "
            f"{summary.existing.get(kind, 0)} ya existían"
        )
    print(
        f"Para el {fecha.isoformat()}: {totales['pedidos_pendientes']} pedidos "
        f"PENDIENTE y {totales['vehiculos_activos']} vehículos ACTIVO."
    )
    print(f"Límite de búsqueda del motor: {settings.optimizacion_tiempo_limite_s} s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
