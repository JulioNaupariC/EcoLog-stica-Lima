"""ECL-63: measure existing SELECTs on a dedicated synthetic test database."""

import argparse
import json
import os
import platform
import statistics
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url

from app.models.cliente import Cliente
from app.models.pedido import Pedido

DATABASE_NAME = "ecologistica_ecl63_queries_test"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed", action="store_true", help="Seed empty test tables only"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    url = make_url(os.environ["DATABASE_URL"])
    if url.database != DATABASE_NAME:
        raise SystemExit("Dedicated ECL-63 test database required")
    engine = create_engine(url, hide_parameters=True)
    try:
        with engine.begin() as conn:
            if args.seed:
                if conn.scalar(text("SELECT count(*) FROM cliente")) or conn.scalar(
                    text("SELECT count(*) FROM pedido")
                ):
                    raise SystemExit("Refusing to seed nonempty tables")
                conn.execute(
                    text("""
                    INSERT INTO cliente (cliente_id, nombre, referencia)
                    SELECT md5('ecl63-client-' || i)::uuid,
                           'Cliente sintetico ' || i, 'Referencia sintetica'
                    FROM generate_series(1, 100) i
                """)
                )
                conn.execute(
                    text("""
                    INSERT INTO pedido (
                        pedido_id, cliente_id, direccion, referencia, ubicacion,
                        peso_kg, volumen_m3, ventana_inicio, ventana_fin,
                        prioridad, tipo_producto, estado
                    )
                    SELECT md5('ecl63-order-' || i)::uuid,
                           md5('ecl63-client-' || (1 + (i % 100)))::uuid,
                           'Direccion sintetica ' || i, 'Referencia sintetica',
                           ST_SetSRID(ST_MakePoint(-77.03, -12.04),4326)::geography,
                           5, 0.1,
                           timestamptz '2026-07-01 05:00:00-05'
                               + (i / 1000) * interval '1 day'
                               + (i % 1000) * interval '1 minute',
                           timestamptz '2026-07-01 05:00:00-05'
                               + (i / 1000) * interval '1 day'
                               + (i % 1000) * interval '1 minute'
                               + interval '1 hour',
                           'ESTANDAR', 'GENERAL',
                           CASE WHEN i % 10 = 0 THEN 'PENDIENTE'
                                ELSE 'ENTREGADO' END
                    FROM generate_series(0, 99999) i
                """)
                )
                conn.execute(text("ANALYZE cliente"))
                conn.execute(text("ANALYZE pedido"))

        with engine.connect() as conn, conn.begin():
            conn.execute(text("SET TRANSACTION READ ONLY"))
            conn.execute(text("SET LOCAL statement_timeout = '10s'"))
            client_id = conn.scalar(
                text("SELECT cliente_id FROM cliente ORDER BY cliente_id LIMIT 1")
            )
            order_id = conn.scalar(
                text("SELECT pedido_id FROM pedido ORDER BY pedido_id LIMIT 1")
            )
            if not client_id or not order_id:
                raise SystemExit("Synthetic dataset required")
            geometry = Pedido.ubicacion.cast(Geometry(geometry_type="POINT", srid=4326))
            queries = {
                "cliente_exists": (
                    select(Cliente).where(Cliente.cliente_id == UUID(str(client_id))),
                    "Existing ClienteRepository.exists: cold identity-map SELECT",
                ),
                "pedido_coordinates": (
                    select(func.ST_Y(geometry), func.ST_X(geometry)).where(
                        Pedido.pedido_id == UUID(str(order_id))
                    ),
                    "Existing PedidoRepository.coordinates",
                ),
                "candidate_pending_window": (
                    text(
                        "SELECT pedido_id, ventana_inicio FROM pedido "
                        "WHERE estado = 'PENDIENTE' "
                        "AND ventana_inicio >= '2026-10-01 05:00:00-05'::timestamptz "
                        "ORDER BY ventana_inicio LIMIT 50"
                    ),
                    "Prospective query only: no production listing endpoint",
                ),
            }
            metadata = {
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "database": DATABASE_NAME,
                "python": platform.python_version(),
                "postgresql": conn.scalar(text("SELECT version()")),
                "postgis": conn.scalar(text("SELECT PostGIS_Lib_Version()")),
                "cliente_count": conn.scalar(text("SELECT count(*) FROM cliente")),
                "pedido_count": conn.scalar(text("SELECT count(*) FROM pedido")),
                "states": dict(
                    conn.execute(
                        text("SELECT estado, count(*) FROM pedido GROUP BY estado")
                    ).all()
                ),
                "indexes": [
                    dict(row)
                    for row in conn.execute(
                        text(
                            "SELECT tablename, indexname, indexdef FROM pg_indexes "
                            "WHERE schemaname='public' "
                            "AND tablename IN ('cliente','pedido') "
                            "ORDER BY tablename,indexname"
                        )
                    ).mappings()
                ],
                "dashboard": {
                    "status": "NOT_IMPLEMENTED",
                    "bytes": None,
                    "limit_bytes": 250000,
                    "passes": None,
                },
                "routes": {"status": "NOT_IMPLEMENTED", "plans": []},
                "method": "Five sequential SELECT EXPLAIN ANALYZE BUFFERS JSON runs; "
                "cache uncontrolled, no concurrent load, no HTTP latency",
                "queries": {},
            }
            args.output.mkdir(parents=True, exist_ok=True)
            for name, (statement, scope) in queries.items():
                sql = str(
                    statement.compile(
                        dialect=engine.dialect, compile_kwargs={"literal_binds": True}
                    )
                )
                plans = [
                    conn.scalar(text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql))
                    for _ in range(5)
                ]
                evidence = {"scope": scope, "sql": sql, "runs": plans}
                (args.output / (name + ".json")).write_text(
                    json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                metadata["queries"][name] = {
                    "scope": scope,
                    "execution_ms": [p[0]["Execution Time"] for p in plans],
                    "median_execution_ms": statistics.median(
                        p[0]["Execution Time"] for p in plans
                    ),
                    "planning_ms": [p[0]["Planning Time"] for p in plans],
                    "plan_file": name + ".json",
                }
            (args.output / "resultados.json").write_text(
                json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(
                json.dumps(
                    {
                        k: v["median_execution_ms"]
                        for k, v in metadata["queries"].items()
                    }
                )
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
