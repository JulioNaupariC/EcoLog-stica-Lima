"""Compare actual client lookup SQL before/after ECL-64 on ST-037 test data."""

import argparse
import json
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.repositories.clientes import ClienteRepository


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    url = make_url(os.environ["DATABASE_URL"])
    if url.database != "ecologistica_ecl63_queries_test":
        raise SystemExit("Dedicated ST-037 synthetic database required")
    engine = create_engine(url, hide_parameters=True)
    evidence: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline": "bc512a5",
        "method": "20 alternating paired EXPLAIN ANALYZE BUFFERS runs per case; "
        "actual Session.get SQL versus actual ClienteRepository.exists SQL",
        "cases": {},
        "dashboard": {"bytes": None, "passes": None, "limit_bytes": 250000},
    }
    try:
        with engine.connect() as conn, conn.begin():
            conn.execute(text("SET TRANSACTION READ ONLY"))
            conn.execute(text("SET LOCAL statement_timeout = '10s'"))
            evidence["postgresql"] = conn.scalar(text("SELECT version()"))
            evidence["counts"] = {
                "clientes": conn.scalar(text("SELECT count(*) FROM cliente")),
                "pedidos": conn.scalar(text("SELECT count(*) FROM pedido")),
            }
            existing = conn.scalar(
                text("SELECT cliente_id FROM cliente ORDER BY cliente_id LIMIT 1")
            )
            if existing is None:
                raise SystemExit("ST-037 synthetic dataset required")
            for case, identifier in {
                "existing": existing,
                "missing": UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
            }.items():
                statements = {}
                outcomes = {}
                for variant in ("before", "after"):
                    captured = []

                    def record(
                        connection, cursor, statement, parameters, context, executemany
                    ):
                        captured.append((statement, parameters))

                    event.listen(conn, "before_cursor_execute", record)
                    try:
                        with Session(bind=conn) as session:
                            result = (
                                session.get(Cliente, identifier) is not None
                                if variant == "before"
                                else ClienteRepository(session).exists(identifier)
                            )
                            outcomes[variant] = {
                                "exists": result,
                            }
                    finally:
                        event.remove(conn, "before_cursor_execute", record)
                    statements[variant] = captured[0]
                assert outcomes["before"]["exists"] == outcomes["after"]["exists"]
                plans = {"before": [], "after": []}
                for iteration in range(20):
                    order = (
                        ("before", "after")
                        if iteration % 2 == 0
                        else ("after", "before")
                    )
                    for variant in order:
                        sql, parameters = statements[variant]
                        plan = conn.exec_driver_sql(
                            "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql,
                            parameters,
                        ).scalar_one()
                        plans[variant].append(plan)
                evidence["cases"][case] = {
                    "identifier": str(identifier),
                    "outcomes": outcomes,
                    "variants": {
                        name: {
                            "sql": sql,
                            "parameters": {k: str(v) for k, v in parameters.items()},
                            "median_execution_ms": statistics.median(
                                p[0]["Execution Time"] for p in plans[name]
                            ),
                            "runs": plans[name],
                        }
                        for name, (sql, parameters) in statements.items()
                    },
                }
            # Internal datum lengths only: excludes protocol/row/header overhead.
            evidence["existing_result_datum_bytes"] = dict(
                conn.execute(
                    text(
                        "SELECT COALESCE(pg_column_size(cliente_id),0) + "
                        "COALESCE(pg_column_size(nombre),0) + "
                        "COALESCE(pg_column_size(horario_preferido),0) + "
                        "COALESCE(pg_column_size(referencia),0) + "
                        "COALESCE(pg_column_size(restriccion_acceso),0) AS before, "
                        "pg_column_size(true) AS after "
                        "FROM cliente WHERE cliente_id = :id"
                    ),
                    {"id": existing},
                )
                .mappings()
                .one()
            )
            args.output.mkdir(parents=True, exist_ok=True)
            (args.output / "comparacion.json").write_text(
                json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
            )
            print(
                json.dumps(
                    {
                        "medians_ms": {
                            case: {
                                v: x["median_execution_ms"]
                                for v, x in data["variants"].items()
                            }
                            for case, data in evidence["cases"].items()
                        },
                        "datum_bytes": evidence["existing_result_datum_bytes"],
                    }
                )
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
