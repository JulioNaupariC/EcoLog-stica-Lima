"""Datos ficticios para la demostración del Sprint 2.

Uso (desde ``backend/``, con la base ya migrada a ``head``)::

    python -m scripts.seed_demo

Requisitos:

* ``DATABASE_URL`` debe apuntar a una base cuyo nombre termine en ``_demo``;
  en otro caso el script se niega a ejecutarse. También se niega con
  ``APP_ENV=production``.
* Las contraseñas se leen de ``SEED_DEMO_PASSWORD_<ROL>`` (ADMINISTRADOR,
  OPERADOR, CONDUCTOR, ANALISTA y AUDITOR). Nunca se escriben en el repositorio
  ni se imprimen.

Todas las escrituras usan los servicios de la aplicación (credenciales,
vehículos, conductores, preferencias, pedidos y asignaciones). La única
excepción es el alta de clientes: no existe un servicio de creación de
clientes (su CRUD está fuera del alcance del Sprint 2), así que se insertan
mediante el modelo ORM, nunca con SQL directo.

Es idempotente: si un dato ya existe (por correo, nombre, placa, DNI o
referencia del pedido), no se duplica.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.rbac import Rol
from app.db.session import build_engine, session_factory
from app.models.cliente import Cliente
from app.models.conductor import Conductor
from app.models.pedido import Pedido
from app.repositories.usuarios import UsuarioRepository
from app.schemas.conductor import ConductorCreate, ConductorUpdate
from app.schemas.pedido import PedidoCreate
from app.schemas.preferencias import PreferenciasPatch
from app.schemas.vehiculo import VehicleCreate
from app.services.conductores import ConductorService
from app.services.credenciales import CredentialService
from app.services.driver_reports import DriverReportService
from app.services.pedidos import PedidoService
from app.services.preferencias import PreferenciasService
from app.services.vehiculos import VehicleDuplicatePlate, VehiculoService

LIMA = ZoneInfo("America/Lima")
DEMO_SUFFIX = "_demo"
PASSWORD_PREFIX = "SEED_DEMO_PASSWORD_"
MIN_PASSWORD_LENGTH = 12
STOP_NAMESPACE = uuid5(NAMESPACE_URL, "https://ecologistica.example/demo/paradas")


class SeedRefused(RuntimeError):
    """The target or configuration is not a safe demo environment."""


# --- Datos ficticios -------------------------------------------------------

# The CONDUCTOR account is the first demo driver (created with its profile below).
USERS = {
    role: f"{role.value.lower()}.demo@ecologistica.example"
    for role in Rol
    if role is not Rol.CONDUCTOR
}

CLIENTS: tuple[tuple[str, str | None, str | None, str | None], ...] = (
    # (nombre, horario_preferido, referencia, restriccion_acceso)
    (
        "Bodega Ficticia Norte",
        "Mañana (preferido)",
        "Puerta junto al parque",
        "Ingreso por puerta lateral",
    ),
    ("Farmacia Ejemplo Centro", "Tarde (preferido)", "Frente a la plaza", None),
    (
        "Minimarket Demo Surco",
        "Lunes a viernes, de 09:00 a 12:00",
        "Esquina con semáforo",
        "Avisar a recepción",
    ),
    ("Librería Imaginaria Miraflores", None, "Local con toldo azul", None),
    ("Restaurante Ficticio Barranco", "Antes de las 11:00", None, "Estacionar atrás"),
    ("Panadería Demo San Borja", "Muy temprano", "Al costado del grifo", None),
    ("Ferretería Ejemplo Lince", None, None, None),
    ("Florería Ficticia Jesús María", "Mediodía", "Portón verde", "Tocar timbre 2"),
)

VEHICLES: tuple[tuple[str, str, str, str, str, str, int], ...] = (
    # (placa, tipo, capacidad_kg, capacidad_m3, km/l, kg CO2/km, año)
    ("DEMO-001", "CAMIONETA", "1200", "8.50", "11.500", "0.21000", 2022),
    ("DEMO-002", "FURGON", "2500", "14.00", "8.200", "0.29000", 2021),
    ("DEMO-003", "FURGON", "2000", "12.00", "9.000", "0.27000", 2023),
    ("DEMO-004", "MOTO", "90", "0.40", "35.000", "0.06000", 2024),
    ("DEMO-005", "CAMIONETA", "1000", "7.00", "12.000", "0.20000", 2020),
)


@dataclass(frozen=True)
class DemoDriver:
    nombre: str
    dni: str
    licencia: str
    email: str
    telefono: str
    licencia_vencida: bool = False
    sin_disponibilidad: bool = False


DRIVERS = (
    DemoDriver(
        "Conductora Demo Uno",
        "90000001",
        "Q-DEMO-01",
        "conductor.demo@ecologistica.example",
        "+51900000001",
    ),
    DemoDriver(
        "Conductor Demo Dos",
        "90000002",
        "Q-DEMO-02",
        "conductor2.demo@ecologistica.example",
        "+51900000002",
    ),
    DemoDriver(
        "Conductor Demo Licencia Vencida",
        "90000003",
        "Q-DEMO-03",
        "conductor3.demo@ecologistica.example",
        "+51900000003",
        licencia_vencida=True,
    ),
    DemoDriver(
        "Conductora Demo Sin Disponibilidad",
        "90000004",
        "Q-DEMO-04",
        "conductor4.demo@ecologistica.example",
        "+51900000004",
        sin_disponibilidad=True,
    ),
)

ORDER_COUNT = 20
ASSIGNED_ORDERS = 5
PRIORITIES = ("EXPRESS", "ESTANDAR", "ECONOMICO", "ESTANDAR")
PRODUCTS = ("Abarrotes", "Farmacia", "Libros", "Perecible", "Ferretería")


@dataclass
class SeedSummary:
    created: dict[str, int] = field(default_factory=dict)
    existing: dict[str, int] = field(default_factory=dict)

    def count(self, kind: str, *, created: bool) -> None:
        target = self.created if created else self.existing
        target[kind] = target.get(kind, 0) + 1


# --- Protecciones ----------------------------------------------------------


def ensure_demo_target(database_url: str | None, app_env: str | None) -> None:
    """Refuse anything that is not an explicit, non-production demo database."""
    if (app_env or "").strip().lower() == "production":
        raise SeedRefused("No se siembran datos ficticios con APP_ENV=production.")
    if not database_url:
        raise SeedRefused("Falta DATABASE_URL.")
    try:
        name = make_url(database_url).database
    except (ArgumentError, ValueError):
        raise SeedRefused("DATABASE_URL no es válida.") from None
    if not name or not name.endswith(DEMO_SUFFIX):
        raise SeedRefused(
            f"La base de datos debe terminar en '{DEMO_SUFFIX}'; no se modificó nada."
        )


def read_passwords(environ: Mapping[str, str]) -> dict[Rol, str]:
    passwords: dict[Rol, str] = {}
    missing = []
    for role in Rol:
        value = environ.get(PASSWORD_PREFIX + role.value, "")
        if len(value) < MIN_PASSWORD_LENGTH:
            missing.append(PASSWORD_PREFIX + role.value)
        else:
            passwords[role] = value
    if missing:
        raise SeedRefused(
            "Defina contraseñas de al menos "
            f"{MIN_PASSWORD_LENGTH} caracteres en: {', '.join(missing)}."
        )
    return passwords


# --- Siembra ---------------------------------------------------------------


def _ensure_users(
    factory: sessionmaker[Session],
    passwords: Mapping[Rol, str],
    summary: SeedSummary,
) -> dict[Rol, UUID]:
    ids: dict[Rol, UUID] = {}
    for role, email in USERS.items():
        with factory.begin() as session:
            repository = UsuarioRepository(session)
            account = repository.find_for_login(email)
            if account is None:
                identity = CredentialService(repository).create(
                    email, passwords[role], role.value
                )
                ids[role] = identity.usuario_id
                summary.count("usuarios", created=True)
            else:
                ids[role] = account.usuario_id
                summary.count("usuarios", created=False)
    return ids


def _ensure_clients(factory: sessionmaker[Session], summary: SeedSummary) -> list[UUID]:
    ids: list[UUID] = []
    preferences = PreferenciasService(factory)
    for nombre, horario, referencia, restriccion in CLIENTS:
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
        preferences.update(
            cliente_id,
            PreferenciasPatch(
                horario_preferido=horario,
                referencia=referencia,
                restriccion_acceso=restriccion,
            ),
        )
        ids.append(cliente_id)
    return ids


def _ensure_vehicles(factory: sessionmaker[Session], summary: SeedSummary) -> None:
    service = VehiculoService(factory)
    for placa, tipo, kg, m3, km_l, co2, year in VEHICLES:
        try:
            service.create(
                VehicleCreate(
                    placa=placa,
                    tipo=tipo,
                    capacidad_kg=Decimal(kg),
                    capacidad_m3=Decimal(m3),
                    rendimiento_km_l=Decimal(km_l),
                    factor_co2_kg_km=Decimal(co2),
                    anio_fabricacion=year,
                )
            )
            summary.count("vehiculos", created=True)
        except VehicleDuplicatePlate:
            summary.count("vehiculos", created=False)


def _ensure_drivers(
    factory: sessionmaker[Session],
    password: str,
    actor_id: UUID,
    now: datetime,
    summary: SeedSummary,
) -> dict[str, UUID]:
    """Return ``dni -> usuario_id`` of each demo driver."""
    service = ConductorService(factory)
    accounts: dict[str, UUID] = {}
    start = now - timedelta(hours=1)
    for driver in DRIVERS:
        with factory() as session:
            row = session.execute(
                select(Conductor.conductor_id, Conductor.usuario_id).where(
                    Conductor.dni == driver.dni
                )
            ).first()
        if row is not None:
            accounts[driver.dni] = row.usuario_id
            summary.count("conductores", created=False)
            continue
        license_until = (
            now.date() - timedelta(days=30)
            if driver.licencia_vencida
            else date(now.year + 3, 12, 31)
        )
        created = service.create(
            ConductorCreate(
                nombre=driver.nombre,
                dni=driver.dni,
                licencia_numero=driver.licencia,
                licencia_vigente_hasta=license_until,
                experiencia_anios=4,
                telefono=driver.telefono,
                punto_partida="Centro de distribución ficticio, Cercado de Lima",
                disponible_desde=start,
                disponible_hasta=start + timedelta(days=30),
                email=driver.email,
                password=password,
            ),
            actor_id,
        )
        if driver.sin_disponibilidad:
            # The API requires availability on creation; clearing it afterwards
            # is the documented way to make a driver unavailable.
            service.update(
                created.conductor_id,
                ConductorUpdate(disponible_desde=None, disponible_hasta=None),
                actor_id,
            )
        accounts[driver.dni] = created.usuario_id
        summary.count("conductores", created=True)
    return accounts


def _order_reference(index: int) -> str:
    return f"Pedido demo {index:02d}"


def _ensure_orders(
    factory: sessionmaker[Session],
    clients: list[UUID],
    today: date,
    summary: SeedSummary,
) -> list[UUID]:
    service = PedidoService(factory)
    ids: list[UUID] = []
    for index in range(1, ORDER_COUNT + 1):
        reference = _order_reference(index)
        with factory() as session:
            existing = session.scalar(
                select(Pedido.pedido_id).where(Pedido.referencia == reference)
            )
        if existing is not None:
            ids.append(existing)
            summary.count("pedidos", created=False)
            continue
        day = today + timedelta(days=index % 2)
        start = datetime.combine(day, time(8 + index % 8, 0), tzinfo=LIMA)
        created = service.create(
            PedidoCreate(
                cliente_id=clients[index % len(clients)],
                direccion=f"Calle Ficticia {100 + index * 7}, Lima",
                referencia=reference,
                latitud=round(-12.02 - index * 0.004, 6),
                longitud=round(-77.03 - index * 0.003, 6),
                peso_kg=Decimal(5 + index * 3),
                volumen_m3=Decimal("0.050") * index,
                ventana_inicio=start,
                ventana_fin=start + timedelta(hours=2),
                prioridad=PRIORITIES[index % len(PRIORITIES)],
                tipo_producto=PRODUCTS[index % len(PRODUCTS)],
            )
        )
        ids.append(created.pedido_id)
        summary.count("pedidos", created=True)
    return ids


def _ensure_assignments(
    factory: sessionmaker[Session],
    driver_account: UUID,
    orders: list[UUID],
    summary: SeedSummary,
) -> None:
    service = DriverReportService(factory)
    existing = {stop.stop_id for stop in service.list_assignments(driver_account)}
    for position, pedido_id in enumerate(orders[:ASSIGNED_ORDERS], start=1):
        stop_id = uuid5(STOP_NAMESPACE, str(pedido_id))
        # provision_assignment updates an existing stop instead of duplicating it.
        service.provision_assignment(
            stop_id=stop_id,
            owner_id=driver_account,
            position=position,
            pedido_id=pedido_id,
        )
        summary.count("asignaciones", created=stop_id not in existing)


def seed(
    factory: sessionmaker[Session],
    passwords: Mapping[Rol, str],
    *,
    now: datetime | None = None,
) -> SeedSummary:
    """Create or complete the demo dataset; safe to run repeatedly."""
    now = now or datetime.now(LIMA)
    summary = SeedSummary()
    users = _ensure_users(factory, passwords, summary)
    clients = _ensure_clients(factory, summary)
    _ensure_vehicles(factory, summary)
    drivers = _ensure_drivers(
        factory, passwords[Rol.CONDUCTOR], users[Rol.ADMINISTRADOR], now, summary
    )
    orders = _ensure_orders(factory, clients, now.date(), summary)
    _ensure_assignments(factory, drivers[DRIVERS[0].dni], orders, summary)
    return summary


def main(environ: Mapping[str, str] = os.environ) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    settings = Settings()
    database_url = (
        settings.database_url.get_secret_value() if settings.database_url else None
    )
    try:
        ensure_demo_target(database_url, environ.get("APP_ENV", settings.app_env))
        passwords = read_passwords(environ)
    except SeedRefused as error:
        print(f"seed_demo: {error}", file=sys.stderr)
        return 2
    engine = build_engine(settings)
    try:
        summary = seed(session_factory(engine), passwords)
    finally:
        engine.dispose()
    for kind in (
        "usuarios",
        "clientes",
        "vehiculos",
        "conductores",
        "pedidos",
        "asignaciones",
    ):
        print(
            f"{kind}: {summary.created.get(kind, 0)} creados, "
            f"{summary.existing.get(kind, 0)} ya existían"
        )
    accounts = [*USERS.values(), *(driver.email for driver in DRIVERS)]
    print("Cuentas: " + ", ".join(accounts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
