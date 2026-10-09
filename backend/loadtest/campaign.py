"""Create a private local cluster and execute ST-035 without touching shared data."""

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import os
import platform
import secrets
import socket
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

import httpx
import psutil
import psycopg
from alembic.config import Config
from alembic.script import ScriptDirectory
from psycopg import sql
from sqlalchemy import Engine, select, text

from alembic import command
from app.core.config import Settings
from app.db.session import build_engine, session_factory
from app.models import Cliente, Pedido, Sesion, Usuario, Vehiculo
from app.repositories.usuarios import UsuarioRepository
from app.services.credenciales import CredentialService
from loadtest.analysis import (
    HOURLY,
    concurrency_summary,
    percentile,
    schedule,
    summarize,
)
from loadtest.keep_awake import set_awake

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
HIDDEN = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def run_command(args: list[str], **kwargs: object) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, cwd=BACKEND, **HIDDEN, **kwargs)


def free_port(port: int) -> None:
    with socket.socket() as connection:
        connection.bind(("127.0.0.1", port))


def create_dataset(url: str, users: int, password: str) -> tuple[Engine, list[str]]:
    engine = build_engine(Settings(database_url=url, app_env="test"))
    with engine.connect() as connection:
        if connection.execute(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='usuario'"
            )
        ).scalar():
            raise RuntimeError("Refusing nonempty test database")
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.attributes["database_url"] = url
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    command.upgrade(config, "head")
    with engine.connect() as connection:
        revision = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
        if revision != ScriptDirectory.from_config(config).get_current_head():
            raise RuntimeError("Migration revision does not match head")
    factory = session_factory(engine)
    with factory.begin() as session:
        for index in range(users):
            CredentialService(UsuarioRepository(session)).create(
                f"st035-{index}@example.test", password, "OPERADOR"
            )
        clients = [Cliente(nombre=f"Cliente sintetico ST035 {i}") for i in range(100)]
        session.add_all(clients)
        session.flush()
        identifiers = [str(client.cliente_id) for client in clients]
    return engine, identifiers


def login(client: httpx.Client, password: str) -> None:
    response = client.post(
        "/login",
        json={"email": "st035-0@example.test", "password": password},
        timeout=5,
    )
    if response.status_code != 200:
        raise RuntimeError("Preparation login failed")


def prepare_fleet(client: httpx.Client) -> list[str]:
    ids = []
    for index in range(50):
        kind = "CAMIONETA" if index < 20 else "FURGON" if index < 40 else "MOTO"
        response = client.post(
            "/vehiculos",
            json={
                "placa": f"ST{index:04}",
                "tipo": kind,
                "capacidad_kg": "500.00" if kind != "MOTO" else "30.00",
                "capacidad_m3": "3.00" if kind != "MOTO" else "0.10",
                "rendimiento_km_l": "12.000",
                "factor_co2_kg_km": "0.15000",
                "anio_fabricacion": 2024,
            },
            timeout=5,
        )
        if response.status_code != 201:
            raise RuntimeError("Fleet preparation failed")
        ids.append(response.json()["vehiculo_id"])
    return ids


def baseline(
    engine: Engine, clients: list[str], vehicles: list[str], users: int
) -> dict:
    with session_factory(engine).begin() as session:
        # Only this newly created disposable database. No shared database cleanup.
        session.query(Sesion).delete()
        actual_clients = set(map(str, session.scalars(select(Cliente.cliente_id))))
        actual_vehicles = set(map(str, session.scalars(select(Vehiculo.vehiculo_id))))
        roles = list(session.execute(select(Usuario.rol, Usuario.estado)))
        orders = session.query(Pedido).count()
        sessions = session.query(Sesion).count()
        kinds = Counter(session.scalars(select(Vehiculo.tipo)))
        if (
            actual_clients != set(clients)
            or actual_vehicles != set(vehicles)
            or len(roles) != users
            or any(tuple(role) != ("OPERADOR", "ACTIVO") for role in roles)
            or orders
            or sessions
            or kinds != {"CAMIONETA": 20, "FURGON": 20, "MOTO": 10}
        ):
            raise RuntimeError("Baseline verification failed")
        versions = session.execute(
            text("SELECT version(), postgis_full_version()")
        ).one()
        revision = session.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
    return {
        "users": users,
        "clients": clients,
        "vehicles": vehicles,
        "fleet_types": dict(kinds),
        "orders": orders,
        "sessions": sessions,
        "alembic_revision": revision,
        "database_versions": list(versions),
    }


def availability_process(url: str, path: Path) -> tuple[subprocess.Popen, TextIO]:
    stream = path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-m",
            "app.monitoring.poll",
            "--url",
            url,
            "--interval",
            "1",
        ],
        cwd=BACKEND,
        stdout=stream,
        stderr=subprocess.STDOUT,
        **HIDDEN,
    )
    return process, stream


def reconcile(engine: Engine, output: Path, config: dict) -> tuple[dict, list[float]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT pedido_id, cliente_id, referencia FROM pedido")
        ).all()
    persisted = {str(row[0]): (str(row[1]), row[2]) for row in rows}
    with gzip.open(output / "persisted.jsonl.gz", "wt", encoding="utf-8") as stream:
        for identifier, (client, reference) in persisted.items():
            stream.write(
                json.dumps(
                    {
                        "pedido_id": identifier,
                        "cliente_id": client,
                        "reference": reference,
                    }
                )
                + "\n"
            )
    with gzip.open(output / "requests.jsonl.gz", "rt", encoding="utf-8") as stream:
        attempts = [json.loads(line) for line in stream]
    selected = [
        row
        for row in attempts
        if row["phase"] == ("daily" if config["profile"] == "daily" else "stable")
    ]
    summary = summarize(selected, persisted)
    summary["total_persisted_all_phases"] = len(persisted)
    returned = {row["pedido_id"] for row in attempts if row["valid"]}
    summary["persisted_without_valid_response_all_phases"] = len(
        set(persisted) - returned
    )
    summary["profile"] = config["profile"]
    summary["run"] = config["run"]
    monitors = [
        json.loads(line) for line in (output / "monitor.jsonl").read_text().splitlines()
    ]
    summary["setup_failed"] = any(
        row.get("setup_failed")
        or row.get("event") in {"login_failed", "monitor_login_failed"}
        for row in monitors
    )
    summary["ramp_warm_failures"] = sum(
        not row["valid"] for row in attempts if row["phase"] in {"ramp", "warm"}
    )
    samples = [row for row in monitors if "stable_offset" in row]
    summary["concurrency"] = concurrency_summary(samples, config["stable"])
    stable_samples = [
        row for row in samples if 0 <= row["stable_offset"] < config["stable"]
    ]
    summary["generator"] = {
        "max_cpu_percent_one_core_basis": max(
            (row["generator_cpu_percent"] for row in stable_samples), default=None
        ),
        "max_scheduler_lag_seconds": max(
            (row["scheduler_lag_seconds"] for row in stable_samples), default=None
        ),
        "max_host_cpu_percent": max(
            (row["host_cpu_percent"] for row in stable_samples), default=None
        ),
        "max_host_memory_percent": max(
            (row["host_memory_percent"] for row in stable_samples), default=None
        ),
    }
    summary["generator"]["lag_over_one_second_samples"] = sum(
        row["scheduler_lag_seconds"] > 1 for row in stable_samples
    )
    observations = [
        json.loads(line)
        for line in (output / "availability.jsonl").read_text().splitlines()
        if line.startswith("{")
    ]
    successful = sum(row["state"] == "AVAILABLE" for row in observations)
    gaps = sum(
        max(
            0,
            round(
                (
                    datetime.fromisoformat(right["timestamp"])
                    - datetime.fromisoformat(left["timestamp"])
                ).total_seconds()
            )
            - 1,
        )
        for left, right in zip(observations, observations[1:])
    )
    summary["availability"] = {
        "first_utc": observations[0]["timestamp"] if observations else None,
        "last_utc": observations[-1]["timestamp"] if observations else None,
        "samples": len(observations),
        "available": successful,
        "unavailable": len(observations) - successful,
        "estimated_missing_slots": gaps,
        "successful_samples_percent": 100 * successful / len(observations)
        if observations
        else None,
        "conservative_sample_coverage_percent": 100
        * successful
        / (len(observations) + gaps)
        if observations
        else None,
        "monthly_sla": "NOT_MEASURED",
    }
    summary["daily_hourly"] = (
        {
            str(hour): sum(
                row["hour"] == hour and row["valid"] and row["pedido_id"] in persisted
                for row in selected
            )
            for hour in range(5, 22)
        }
        if config["profile"] == "daily"
        else None
    )
    integrity = (
        not summary["setup_failed"]
        and summary["ramp_warm_failures"] == 0
        and summary["functional_or_transport_errors"] == 0
        and summary["persistence_discrepancies"] == 0
        and summary["persisted_without_valid_response_all_phases"] == 0
        and summary["generator"]["lag_over_one_second_samples"] == 0
    )
    summary["load_acceptance_pass"] = (
        integrity
        and summary["p95_threshold_pass"]
        and summary["http_5xx_threshold_pass"]
        and summary["unique_valid_persisted"] >= 1000
        and (
            summary["concurrency"]["sustained_100_pass"]
            if config["profile"] == "stress"
            else summary["attempts"] == 1000
            and summary["http_5xx"] == 0
            and list(summary["daily_hourly"].values()) == list(HOURLY)
        )
    )
    write_json(output / "summary.json", summary)
    return summary, [
        row["seconds"]
        for row in selected
        if row["valid"]
        and persisted.get(row["pedido_id"]) == (row["cliente_id"], row["reference"])
    ]


def execute_profile(
    args: argparse.Namespace,
    name: str,
    password: str,
    scratch: Path,
    evidence: Path,
    admin: psycopg.Connection,
) -> tuple[dict, list[float]]:
    output = evidence / name
    output.mkdir()
    database = f"st035_{scratch.name}_{name}"
    admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    db_url = f"postgresql+psycopg://st035@127.0.0.1:{args.pg_port}/{database}"
    engine, clients = create_dataset(db_url, args.users, password)
    environment = os.environ.copy()
    environment.update(DATABASE_URL=db_url, APP_ENV="test", SESSION_TTL_MINUTES="60")
    log = (output / "api.log").open("w", encoding="utf-8")
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(args.api_port),
            "--workers",
            "1",
            "--no-access-log",
        ],
        cwd=BACKEND,
        env=environment,
        stdout=log,
        stderr=subprocess.STDOUT,
        **HIDDEN,
    )
    url = f"http://127.0.0.1:{args.api_port}"
    observer = None
    observed_stream = None
    try:
        with httpx.Client(base_url=url, trust_env=False) as client:
            for _ in range(100):
                try:
                    if client.get("/health/ready", timeout=2).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.2)
            else:
                raise RuntimeError("Isolated API did not become ready")
            login(client, password)
            vehicles = prepare_fleet(client)
        write_json(
            output / "baseline.json", baseline(engine, clients, vehicles, args.users)
        )
        config = {
            "run": name,
            "profile": "daily" if name == "daily" else "stress",
            "output": str(output),
            "url": url,
            "clients": clients,
            "seed": args.seed,
            "schedule": schedule(args.seed),
            "daily_seconds": args.daily_seconds,
            "ramp": args.ramp,
            "warm": args.warm,
            "stable": args.stable,
        }
        write_json(output / "manifest.json", config)
        environment.update(
            ST035_CONFIG=str(output / "manifest.json"), ST035_PASSWORD=password
        )
        observer, observed_stream = availability_process(
            url, output / "availability.jsonl"
        )
        daily = name == "daily"
        duration = (
            args.daily_seconds + 30
            if daily
            else args.ramp + args.warm + args.stable + 1
        )
        count = 1 if daily else args.users
        with (output / "locust.log").open("w", encoding="utf-8") as stream:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "locust",
                    "-f",
                    "loadtest/locustfile.py",
                    "--headless",
                    "--host",
                    url,
                    "--users",
                    str(count),
                    "--spawn-rate",
                    "1" if daily else str(args.users / args.ramp),
                    "--run-time",
                    f"{duration}s",
                    "--stop-timeout",
                    "15",
                    "--only-summary",
                    "--exit-code-on-error",
                    "0",
                    "--csv",
                    str(output / "locust"),
                    "--html",
                    str(output / "locust.html"),
                ],
                cwd=BACKEND,
                env=environment,
                stdout=stream,
                stderr=subprocess.STDOUT,
                **HIDDEN,
            )
        if result.returncode:
            raise RuntimeError("Load generator failed; inspect locust.log")
        observer.terminate()
        observer.wait(timeout=10)
        observed_stream.close()
        summary, latencies = reconcile(engine, output, config)
        print(json.dumps({"completed": name, **summary}), flush=True)
        return summary, latencies
    finally:
        if observer and observer.poll() is None:
            observer.terminate()
            observer.wait(timeout=10)
        if observed_stream and not observed_stream.closed:
            observed_stream.close()
        api.terminate()
        api.wait(timeout=15)
        log.close()
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pg-port", type=int, default=55455)
    parser.add_argument("--api-port", type=int, default=8055)
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--seed", type=int, default=35061)
    parser.add_argument("--daily-seconds", type=int, default=180)
    parser.add_argument("--ramp", type=int, default=60)
    parser.add_argument("--warm", type=int, default=120)
    parser.add_argument("--stable", type=int, default=600)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument(
        "--profiles",
        nargs="+",
        choices=["daily", "stress1", "stress2", "stress3"],
        help="Optional isolated recovery/subset; defaults to the complete campaign",
    )
    args = parser.parse_args()
    if args.pg_port == args.api_port or not all(
        1 <= port <= 65535 for port in (args.pg_port, args.api_port)
    ):
        parser.error("Use distinct TCP ports in 1..65535")
    if args.profiles and len(args.profiles) != len(set(args.profiles)):
        parser.error("Do not repeat profile names")
    if (
        min(
            args.users,
            args.daily_seconds,
            args.ramp,
            args.warm,
            args.stable,
            args.repetitions,
        )
        <= 0
        or args.users > 300
    ):
        parser.error("Positive parameters and at most 300 users required")
    free_port(args.pg_port)
    free_port(args.api_port)
    evidence = args.output.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    scratch = (
        ROOT / ".tmp-st035-pg" / datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    )
    scratch.mkdir(parents=True, exist_ok=False)
    pg_bin = args.pg_bin.resolve()
    pgctl = str(pg_bin / "pg_ctl.exe" if os.name == "nt" else pg_bin / "pg_ctl")
    initdb = str(pg_bin / "initdb.exe" if os.name == "nt" else pg_bin / "initdb")
    password = secrets.token_urlsafe(32)
    env = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "git_base": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)
        ),
        "platform": platform.platform(),
        "python": sys.version,
        "cpu": platform.processor(),
        "logical_cpus": psutil.cpu_count(),
        "physical_cpus": psutil.cpu_count(logical=False),
        "ram_bytes": psutil.virtual_memory().total,
        "packages": {
            name: importlib.metadata.version(name)
            for name in (
                "locust",
                "fastapi",
                "uvicorn",
                "psycopg",
                "SQLAlchemy",
                "psutil",
            )
        },
        "parameters": {
            key: str(value) if isinstance(value, Path) else value
            for key, value in vars(args).items()
        },
        "workers": 1,
        "replicas": 1,
        "network": "127.0.0.1; generator/API/DB same host",
        "business_pool": "SQLAlchemy defaults: pool_size=5, max_overflow=10",
        "audit_pool": "separate SQLAlchemy pool: pool_size=5, max_overflow=10",
        "clocks": "same host OS epoch; each process uses perf_counter for durations",
        "daily_profile": "COMPRESSED_SIMULATION"
        if args.daily_seconds != 61200
        else "REAL_TIME",
        "monthly_sla": "NOT_MEASURED",
    }
    write_json(evidence / "environment.json", env)
    results = []
    aggregate = []
    cluster_started = False
    set_awake(True)
    try:
        run_command(
            [
                initdb,
                "-D",
                str(scratch / "data"),
                "-U",
                "st035",
                "--auth-local=trust",
                "--auth-host=trust",
                "--encoding=UTF8",
            ],
            stdout=subprocess.DEVNULL,
        )
        with (scratch / "data" / "postgresql.conf").open("a") as stream:
            stream.write(f"\nlisten_addresses='127.0.0.1'\nport={args.pg_port}\n")
        run_command(
            [
                pgctl,
                "-D",
                str(scratch / "data"),
                "-l",
                str(scratch / "postgres.log"),
                "-w",
                "start",
            ],
            stdout=subprocess.DEVNULL,
        )
        cluster_started = True
        with psycopg.connect(
            host="127.0.0.1",
            port=args.pg_port,
            user="st035",
            dbname="postgres",
            autocommit=True,
        ) as admin:
            for name in args.profiles or (
                ["daily"] + [f"stress{i}" for i in range(1, args.repetitions + 1)]
            ):
                print(
                    f"Preparing {name}: new database, users, 100 clients, 50 vehicles",
                    flush=True,
                )
                result, latencies = execute_profile(
                    args, name, password, scratch, evidence, admin
                )
                results.append(result)
                if name != "daily":
                    aggregate.extend(latencies)
        write_json(
            evidence / "campaign.json",
            {
                "results": results,
                "aggregate_stress_p95_seconds": percentile(aggregate),
                "aggregate_population": len(aggregate),
                "all_load_profiles_pass": all(
                    row["load_acceptance_pass"] for row in results
                ),
                "methodology_durations_match_plan": (
                    args.ramp,
                    args.warm,
                    args.stable,
                    args.repetitions,
                )
                == (60, 120, 600, 3)
                and args.profiles is None,
                "rnf008_integral": "PENDING_DASHBOARD_ECL15",
                "monthly_sla": "NOT_MEASURED",
            },
        )
    finally:
        set_awake(False)
        if cluster_started:
            run_command(
                [pgctl, "-D", str(scratch / "data"), "-m", "fast", "-w", "stop"],
                stdout=subprocess.DEVNULL,
            )
        if (scratch / "postgres.log").exists():
            (evidence / "postgres.log").write_bytes(
                (scratch / "postgres.log").read_bytes()
            )
        checksums = {}
        for path in evidence.rglob("*"):
            if path.is_file():
                checksums[str(path.relative_to(evidence))] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
        write_json(evidence / "sha256.json", checksums)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
