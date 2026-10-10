"""Disposable real-browser/API/PostGIS verification for ST-032. No shared DB."""

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
from alembic.config import Config
from sqlalchemy import func, select, text

from alembic import command
from app.core.config import Settings
from app.db.session import build_engine, session_factory
from app.models import Cliente, Pedido
from app.models.driver_report import DriverReport
from app.repositories.usuarios import UsuarioRepository
from app.services.credenciales import CredentialService
from app.services.driver_reports import DriverReportService

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
HIDDEN = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def run(args: list[str], cwd: Path = BACKEND, **kwargs):
    return subprocess.run(args, cwd=cwd, check=True, **HIDDEN, **kwargs)


def wait_for(url: str, process: subprocess.Popen) -> None:
    with httpx.Client(timeout=1, trust_env=False) as client:
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError("Isolated test process exited; inspect its log")
            try:
                if client.get(url).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
    raise RuntimeError("Isolated test process failed to start")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pg-bin", required=True)
    parser.add_argument("--playwright-module", required=True)
    parser.add_argument("--integration-only", action="store_true")
    args = parser.parse_args()
    pg = Path(args.pg_bin).resolve()
    for port in (55456, 8056, 5179):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", port))
    private = (
        ROOT / ".tmp-st032-pg" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    )
    private.mkdir(parents=True)
    data = private / "data"
    output = FRONTEND / "evidencias" / "ECL-58"
    output.mkdir(parents=True, exist_ok=True)
    processes, streams = [], []
    engine = None
    started = False
    try:
        with (private / "initdb.log").open("w") as log:
            run(
                [
                    str(pg / "initdb.exe"),
                    "-D",
                    str(data),
                    "-U",
                    "postgres",
                    "-A",
                    "trust",
                    "--no-locale",
                    "--encoding=UTF8",
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        # Trust is ONLY for this fresh, disposable cluster listening on loopback.
        run(
            [
                str(pg / "pg_ctl.exe"),
                "-D",
                str(data),
                "-l",
                str(private / "postgres.log"),
                "-o",
                "-h 127.0.0.1 -p 55456",
                "-w",
                "start",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        started = True
        run(
            [
                str(pg / "createdb.exe"),
                "-h",
                "127.0.0.1",
                "-p",
                "55456",
                "-U",
                "postgres",
                "st032_test",
            ],
            capture_output=True,
        )
        url = "postgresql+psycopg://postgres@127.0.0.1:55456/st032_test"
        engine = build_engine(Settings(database_url=url, app_env="test"))
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION postgis"))
        config = Config(str(BACKEND / "alembic.ini"))
        config.attributes["database_url"] = url
        command.upgrade(config, "head")
        # Verify downgrade/upgrade of the added link on this empty isolated schema.
        command.downgrade(config, "0008_driver_reports")
        command.upgrade(config, "head")
        factory = session_factory(engine)
        if args.integration_only:
            command.downgrade(config, "base")
            test_env = dict(
                os.environ,
                TEST_DATABASE_URL=url,
                DATABASE_URL="postgresql+psycopg://postgres@127.0.0.1:55456/st032_unused",
            )
            with (output / "integration.log").open("w", encoding="utf-8") as log:
                run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "tests/integration/test_driver_stop_order.py",
                        "tests/integration/test_driver_reports_migration.py",
                        "-q",
                        "-o",
                        "addopts=",
                        "-p",
                        "no:cacheprovider",
                        "--basetemp=" + str(private / "pytest-temp"),
                        "--junitxml=" + str(output / "integration-tests.xml"),
                    ],
                    env=test_env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
            print("ST032: isolated integration/migration tests passed.")
            return
        password = secrets.token_urlsafe(24)
        identities = {}
        with factory.begin() as session:
            for name in ("chrome", "firefox", "other", "operator"):
                user = CredentialService(UsuarioRepository(session)).create(
                    f"st032-{name}@example.test",
                    password,
                    "OPERADOR" if name == "operator" else "CONDUCTOR",
                )
                identities[name] = user.usuario_id
            cliente = Cliente(nombre="Cliente sintetico ST032")
            session.add(cliente)
            session.flush()
            client_id = cliente.cliente_id
        assignments = []
        for browser in ("chrome", "firefox"):
            for position in range(1, 11):
                with factory.begin() as session:
                    order = Pedido(
                        cliente_id=client_id,
                        direccion=f"Av. Sintetica {position} - {browser}",
                        referencia="Puerta de prueba",
                        peso_kg=Decimal("1.00"),
                        volumen_m3=Decimal("0.01"),
                        ventana_inicio=datetime.now(timezone.utc),
                        ventana_fin=datetime.now(timezone.utc) + timedelta(hours=2),
                        prioridad="ESTANDAR",
                        tipo_producto="GENERAL",
                    )
                    session.add(order)
                    session.flush()
                    order_id = order.pedido_id
                stop_id = uuid4()
                DriverReportService(factory).provision_assignment(
                    stop_id=stop_id,
                    owner_id=identities[browser],
                    position=position,
                    pedido_id=order_id,
                )
                assignments.append(
                    {
                        "browser": browser,
                        "position": position,
                        "stop_id": str(stop_id),
                        "pedido_id": str(order_id),
                    }
                )
        env = dict(
            os.environ,
            DATABASE_URL=url,
            APP_ENV="test",
            CORS_ALLOWED_ORIGINS='["http://127.0.0.1:5179"]',
        )
        api_log = (output / "api.log").open("w", encoding="utf-8")
        streams.append(api_log)
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
                "8056",
            ],
            cwd=BACKEND,
            env=env,
            stdout=api_log,
            stderr=subprocess.STDOUT,
            **HIDDEN,
        )
        processes.append(api)
        wait_for("http://127.0.0.1:8056/health", api)
        build_env = dict(os.environ, VITE_API_BASE_URL="http://127.0.0.1:8056")
        with (output / "build.log").open("w", encoding="utf-8") as log:
            # Node executables avoid shell quoting and PowerShell execution policy.
            run(
                ["node", "node_modules/typescript/bin/tsc", "-b"],
                cwd=FRONTEND,
                env=build_env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            run(
                ["node", "node_modules/vite/bin/vite.js", "build"],
                cwd=FRONTEND,
                env=build_env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            run(
                ["node", "scripts/build-offline.mjs"],
                cwd=FRONTEND,
                env=build_env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        preview_log = (private / "preview.log").open("w")
        streams.append(preview_log)
        preview = subprocess.Popen(
            [
                "node",
                "node_modules/vite/bin/vite.js",
                "preview",
                "--host",
                "127.0.0.1",
                "--port",
                "5179",
                "--strictPort",
            ],
            cwd=FRONTEND,
            stdout=preview_log,
            stderr=subprocess.STDOUT,
            **HIDDEN,
        )
        processes.append(preview)
        wait_for("http://127.0.0.1:5179", preview)
        browser_env = dict(
            os.environ,
            PLAYWRIGHT_MODULE=str(Path(args.playwright_module).resolve()),
            OFFLINE_API_URL="http://127.0.0.1:8056",
            OFFLINE_PREVIEW_URL="http://127.0.0.1:5179",
            OFFLINE_TEST_PASSWORD=password,
        )
        with (output / "browser.log").open("w", encoding="utf-8") as log:
            run(
                ["node", "scripts/verify-offline.mjs"],
                cwd=FRONTEND,
                env=browser_env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        with factory() as session:
            reports = list(session.scalars(select(DriverReport)))
            assert len(reports) == 20
            assert session.scalar(select(func.count(DriverReport.operation_id))) == 20
            persisted = [
                {
                    "operation_id": str(row.operation_id),
                    "stop_id": str(row.stop_id),
                    "status": row.status,
                }
                for row in reports
            ]
        # Real endpoint negative permission/ownership cases.
        negative = []
        for name, expected in (("other", 404), ("operator", 403)):
            with httpx.Client(base_url="http://127.0.0.1:8056") as client:
                assert (
                    client.post(
                        "/login",
                        json={
                            "email": f"st032-{name}@example.test",
                            "password": password,
                        },
                    ).status_code
                    == 200
                )
                response = client.post(
                    "/conductor/reportes",
                    json={
                        "operation_id": str(uuid4()),
                        "stop_id": assignments[0]["stop_id"],
                        "status": "ENTREGADO",
                    },
                )
                assert response.status_code == expected
                negative.append(
                    {"role": name, "expected": expected, "actual": response.status_code}
                )
        with engine.connect() as connection:
            revision = connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )
            versions = list(
                connection.execute(
                    text("SELECT version(), postgis_full_version()")
                ).one()
            )
        evidence = {
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "database": "fresh isolated st032_test",
            "migration": revision,
            "database_versions": versions,
            "assignments": assignments,
            "persisted_reports": persisted,
            "expected_reports": 20,
            "actual_reports": len(persisted),
            "negative_cases": negative,
            "credentials_exported": False,
            "migration_upgrade_downgrade": "passed",
        }
        (output / "persistencia.json").write_text(
            json.dumps(evidence, indent=2), encoding="utf-8"
        )
        print(
            "ST032 E2E passed: 20 reports persisted once; "
            "browser retries and negative permissions verified."
        )
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        for stream in streams:
            stream.close()
        if engine is not None:
            engine.dispose()
        if started:
            run(
                [str(pg / "pg_ctl.exe"), "-D", str(data), "-m", "fast", "-w", "stop"],
                capture_output=True,
            )


if __name__ == "__main__":
    main()
