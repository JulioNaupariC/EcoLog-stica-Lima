"""Dataset operativo ficticio para medir el Inicio (ECL-25 / ST-037 y ST-038).

50 vehículos, 200 conductores y 30 días × 1 000 pedidos (30 000), insertados en
bloque con ``generate_series``. Solo para bases ``*_test``: lo usan la prueba de
regresión de ``/indicadores/operacion`` y ``measure_home_payload.py``.

Distribución determinista para que los agregados esperados sean conocidos:

* vehículos: 45 ACTIVO y 5 INACTIVO; capacidad 500 + 50 × (n mod 50) kg;
* conductores (por n mod 40): 29/40 habilitados; el resto cubre licencia vencida,
  sin disponibilidad, disponibilidad vencida, cuenta inactiva y conductor inactivo;
* pedidos: estado PENDIENTE (único estado definido en el modelo), prioridad
  EXPRESS 20 %, ESTANDAR 50 %, ECONOMICO 30 %, ubicación dentro de Lima.
"""

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

VEHICLES = 50
DRIVERS = 200
DAYS = 30
ORDERS_PER_DAY = 1_000
CLIENTS = 100


@dataclass(frozen=True)
class ExpectedIndicators:
    vehiculos_total: int
    vehiculos_activos: int
    capacidad_kg_activa: int
    conductores_total: int
    conductores_habilitados: int
    pedidos_total: int
    pedidos_por_prioridad: dict[str, int]


def _driver_case(index: int) -> str:
    bucket = index % 40
    if bucket < 29:
        return "HABILITADO"
    if bucket < 33:
        return "LICENCIA_VENCIDA"
    if bucket < 36:
        return "SIN_DISPONIBILIDAD"
    if bucket < 38:
        return "DISPONIBILIDAD_VENCIDA"
    if bucket < 39:
        return "CUENTA_INACTIVA"
    return "CONDUCTOR_INACTIVO"


def _priority(index: int) -> str:
    bucket = index % 10
    if bucket < 2:
        return "EXPRESS"
    if bucket < 7:
        return "ESTANDAR"
    return "ECONOMICO"


def expected(
    vehicles: int = VEHICLES,
    drivers: int = DRIVERS,
    orders: int = DAYS * ORDERS_PER_DAY,
) -> ExpectedIndicators:
    active = [n for n in range(vehicles) if n % 10 != 9]
    priorities = {"EXPRESS": 0, "ESTANDAR": 0, "ECONOMICO": 0}
    for n in range(orders):
        priorities[_priority(n)] += 1
    return ExpectedIndicators(
        vehiculos_total=vehicles,
        vehiculos_activos=len(active),
        capacidad_kg_activa=sum(500 + 50 * (n % 50) for n in active),
        conductores_total=drivers,
        conductores_habilitados=sum(
            _driver_case(n) == "HABILITADO" for n in range(drivers)
        ),
        pedidos_total=orders,
        pedidos_por_prioridad=priorities,
    )


def seed_operational_dataset(
    session: Session,
    *,
    now: datetime,
    vehicles: int = VEHICLES,
    drivers: int = DRIVERS,
    days: int = DAYS,
    orders_per_day: int = ORDERS_PER_DAY,
) -> None:
    """Insert the dataset; ``now`` must be timezone-aware (America/Lima)."""
    today: date = now.date()
    params = {"now": now, "today": today}
    session.execute(
        text(
            """
            INSERT INTO vehiculo (placa, tipo, capacidad_kg, capacidad_m3,
                rendimiento_km_l, factor_co2_kg_km, anio_fabricacion, estado)
            SELECT 'IND-' || lpad(n::text, 3, '0'),
                   (ARRAY['CAMIONETA','FURGON','MOTO'])[n % 3 + 1],
                   500 + 50 * (n % 50), 4 + n % 10, 8 + n % 7, 0.2 + (n % 5) * 0.05,
                   2015 + n % 10,
                   CASE WHEN n % 10 = 9 THEN 'INACTIVO' ELSE 'ACTIVO' END
            FROM generate_series(0, :count - 1) AS n
            """
        ),
        {"count": vehicles},
    )
    session.execute(
        text(
            """
            INSERT INTO usuario (email, password_hash, rol, estado)
            SELECT 'conductor' || n || '@indicadores.example.test',
                   'no-usado-en-la-medicion', 'CONDUCTOR',
                   CASE WHEN n % 40 = 38 THEN 'INACTIVO' ELSE 'ACTIVO' END
            FROM generate_series(0, :count - 1) AS n
            """
        ),
        {"count": drivers},
    )
    session.execute(
        text(
            """
            INSERT INTO conductor (usuario_id, nombre, dni, licencia_numero,
                licencia_vigente_hasta, experiencia_anios, telefono,
                disponible_desde, disponible_hasta, punto_partida, estado)
            SELECT u.usuario_id, 'Conductor ficticio ' || n, lpad(n::text, 8, '0'),
                   'Q' || lpad(n::text, 8, '0'),
                   CASE WHEN n % 40 BETWEEN 29 AND 32
                        THEN CAST(:today AS date) - 1
                        ELSE CAST(:today AS date) + 365 END,
                   n % 15, '+519' || lpad(n::text, 8, '0'),
                   CASE WHEN n % 40 BETWEEN 33 AND 35 THEN NULL
                        WHEN n % 40 BETWEEN 36 AND 37
                        THEN CAST(:now AS timestamptz) - interval '2 days'
                        ELSE CAST(:now AS timestamptz) - interval '1 hour' END,
                   CASE WHEN n % 40 BETWEEN 33 AND 35 THEN NULL
                        WHEN n % 40 BETWEEN 36 AND 37
                        THEN CAST(:now AS timestamptz) - interval '1 day'
                        ELSE CAST(:now AS timestamptz) + interval '10 hours' END,
                   'Almacén ficticio ' || n % 5,
                   CASE WHEN n % 40 = 39 THEN 'INACTIVO' ELSE 'ACTIVO' END
            FROM generate_series(0, :count - 1) AS n
            JOIN usuario u
              ON u.email = 'conductor' || n || '@indicadores.example.test'
            """
        ),
        {**params, "count": drivers},
    )
    session.execute(
        text(
            """
            INSERT INTO cliente (nombre)
            SELECT 'Cliente ficticio ' || n FROM generate_series(0, :count - 1) AS n
            """
        ),
        {"count": CLIENTS},
    )
    session.execute(
        text(
            """
            WITH clientes AS (
                SELECT cliente_id, row_number() OVER (ORDER BY nombre) - 1 AS pos
                FROM cliente WHERE nombre LIKE 'Cliente ficticio %'
            )
            INSERT INTO pedido (cliente_id, direccion, referencia, ubicacion, peso_kg,
                volumen_m3, ventana_inicio, ventana_fin, prioridad, tipo_producto,
                estado)
            SELECT c.cliente_id, 'Calle Ficticia ' || n, 'Pedido ficticio ' || n,
                   ST_SetSRID(ST_MakePoint(-77.10 + (n % 97) * 0.002,
                                           -12.15 + (n % 89) * 0.002), 4326)::geography,
                   1 + n % 40, 0.05 + (n % 20) * 0.05,
                   d.inicio, d.inicio + interval '2 hours',
                   CASE WHEN n % 10 < 2 THEN 'EXPRESS'
                        WHEN n % 10 < 7 THEN 'ESTANDAR'
                        ELSE 'ECONOMICO' END,
                   (ARRAY['ABARROTES','BEBIDAS','LIMPIEZA','FARMACIA'])[n % 4 + 1],
                   'PENDIENTE'
            FROM generate_series(0, :total - 1) AS n
            JOIN clientes c ON c.pos = n % :clients
            CROSS JOIN LATERAL (
                SELECT ((CAST(:today AS date) - (:days - 1) + n / :per_day)
                        + time '08:00' + (n % 10) * interval '1 hour')
                       AT TIME ZONE 'America/Lima' AS inicio
            ) AS d
            """
        ),
        {
            **params,
            "total": days * orders_per_day,
            "clients": CLIENTS,
            "days": days,
            "per_day": orders_per_day,
        },
    )
