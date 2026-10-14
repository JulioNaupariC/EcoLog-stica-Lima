"""Mide el payload y las consultas del Inicio (ECL-25 / ST-037 y ST-038).

Antes: el Inicio pide ``GET /vehiculos`` (lista completa) y
``GET /conductores?page=1&page_size=100``. Después: ``GET /indicadores/operacion``.
Registra bytes UTF-8 de cada cuerpo JSON, peticiones, sentencias SQL por petición,
mediana de 20 tiempos y, si el repositorio de indicadores existe, el
``EXPLAIN (ANALYZE, BUFFERS)`` de cada consulta agregada (5 ejecuciones).

Solo opera sobre ``ecologistica_ecl25_test`` (``DATABASE_URL`` privado). ``--seed``
aplica las migraciones y siembra ``indicadores_dataset`` sobre tablas vacías. La
cuenta de medición usa una contraseña aleatoria que no se imprime ni se guarda.
"""

import argparse
import json
import os
import platform
import secrets
import statistics
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event, func, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.core.passwords import hash_password
from app.main import create_app
from app.models.pedido import Pedido
from app.models.usuario import Usuario
from app.repositories.usuarios import UsuarioRepository
from app.services.credenciales import CredentialService
from scripts.indicadores_dataset import expected, seed_operational_dataset

DATABASE_NAME = "ecologistica_ecl25_test"
LIMA = ZoneInfo("America/Lima")
EMAIL = "medicion-inicio@indicadores.example.test"
RUNS = 20
BEFORE = ("/vehiculos", "/conductores?page=1&page_size=100")
AFTER = ("/indicadores/operacion",)


class StatementCounter:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self, *_args: object) -> None:
        self.count += 1


def guarded_url() -> str:
    raw = os.environ["DATABASE_URL"]
    if make_url(raw).database != DATABASE_NAME:
        raise SystemExit(f"Solo se permite la base {DATABASE_NAME}")
    return raw


def seed(engine: Engine, raw_url: str) -> str:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.attributes["database_url"] = raw_url
    command.upgrade(config, "head")
    with Session(engine) as session:
        if session.scalar(select(func.count()).select_from(Pedido)):
            raise SystemExit("La base ya tiene pedidos; usa una base nueva")
        seed_operational_dataset(session, now=datetime.now(LIMA))
        session.commit()
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("ANALYZE"))
    return "sembrado"


def server_version(engine: Engine) -> str:
    with engine.connect() as conn:
        return str(conn.scalar(text("SHOW server_version")))


def measurement_password(engine: Engine) -> str:
    password = secrets.token_urlsafe(24)
    with Session(engine) as session, session.begin():
        existing = session.scalar(select(Usuario).where(Usuario.email == EMAIL))
        if existing is None:
            CredentialService(UsuarioRepository(session)).create(
                EMAIL, password, "ADMINISTRADOR"
            )
        else:
            # La auditoría es de solo inserción: se rota la contraseña.
            existing.password_hash = hash_password(password)
    return password


def measure_requests(client: TestClient, paths: tuple[str, ...]) -> dict:
    counter = StatementCounter()
    event.listen(Engine, "before_cursor_execute", counter)
    try:
        results = {}
        for path in paths:
            counter.count = 0
            response = client.get(path)
            statements = counter.count
            timings = []
            for _ in range(RUNS):
                start = time.perf_counter()
                client.get(path)
                timings.append((time.perf_counter() - start) * 1000)
            results[path] = {
                "status": response.status_code,
                "bytes_utf8": len(response.content),
                "sentencias_sql": statements,
                "cache_control": response.headers.get("cache-control"),
                "mediana_ms": round(statistics.median(timings), 2),
            }
    finally:
        event.remove(Engine, "before_cursor_execute", counter)
    available = [item for item in results.values() if item["status"] == 200]
    return {
        "peticiones": len(paths),
        "bytes_utf8_total": sum(item["bytes_utf8"] for item in available),
        "detalle": results,
    }


def home_figures_before(client: TestClient) -> dict:
    """Replica el cálculo del Inicio anterior: habilitados sobre la primera página."""
    vehicles = client.get(BEFORE[0]).json()
    drivers = client.get(BEFORE[1]).json()
    return {
        "vehiculos_total": len(vehicles),
        "vehiculos_activos": sum(item["estado"] == "ACTIVO" for item in vehicles),
        "conductores_total": drivers["total"],
        "habilitados_mostrados": sum(
            item["habilitado_asignacion"] for item in drivers["items"]
        ),
        "conductores_evaluados": len(drivers["items"]),
    }


def explain_aggregates(engine: Engine) -> dict:
    try:
        from app.repositories.indicadores import aggregate_statements
    except ImportError:
        return {"estado": "repositorio de indicadores aún no existe"}
    plans = {}
    with engine.connect() as conn:
        for name, statement in aggregate_statements(datetime.now(LIMA)).items():
            compiled = statement.compile(dialect=postgresql.dialect())
            sql = str(compiled)
            runs = []
            for _ in range(5):
                rows = conn.exec_driver_sql(
                    "EXPLAIN (ANALYZE, BUFFERS) " + sql, compiled.params
                ).scalars()
                runs.append(list(rows))
            times = [
                float(line.split("Execution Time:")[1].split("ms")[0])
                for run in runs
                for line in run
                if "Execution Time:" in line
            ]
            plans[name] = {
                "sql": sql,
                "execution_ms_mediana": round(statistics.median(times), 3),
                "plan_ultima_ejecucion": runs[-1],
            }
    return plans


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fase", choices=("antes", "despues"), required=True)
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw_url = guarded_url()
    engine = create_engine(raw_url)
    seeded = seed(engine, raw_url) if args.seed else "reutilizado"
    password = measurement_password(engine)
    app = create_app(Settings(app_env="test", database_url=raw_url))
    with TestClient(app) as client:
        login = client.post("/login", json={"email": EMAIL, "password": password})
        if login.status_code != 200:
            raise SystemExit("No se pudo iniciar sesión con la cuenta de medición")
        result = {
            "fase": args.fase,
            "fecha": datetime.now(LIMA).isoformat(timespec="seconds"),
            "dataset": seeded,
            "esperado": expected().__dict__,
            "entorno": {
                "python": platform.python_version(),
                "postgresql": server_version(engine),
            },
            "antes": measure_requests(client, BEFORE),
            "cifras_inicio_anterior": home_figures_before(client),
            "despues": measure_requests(client, AFTER),
            "explain": explain_aggregates(engine),
        }
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / f"medicion-{args.fase}.json"
    target.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    summary = {
        key: (result[key]["peticiones"], result[key]["bytes_utf8_total"])
        for key in ("antes", "despues")
    }
    print(f"{target}: {summary}")


if __name__ == "__main__":
    main()
