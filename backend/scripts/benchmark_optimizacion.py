"""EN-003 (ECL-21): end-to-end benchmark of route optimization (RNF-001).

RNF-001: an Operator optimization of up to 150 orders and 15 vehicles finishes
in <= 45 s at the 95th percentile of 30 runs, with fixed seeds and data.

Each run seeds its own synthetic orders and fleet (seed = base + run), logs in
as a synthetic Operator and measures, through the real FastAPI application and
PostgreSQL/PostGIS:

- ``post_s``: wall time of ``POST /optimizaciones`` until the 201 arrives (the
  answer only comes after the whole result is stored);
- ``detalle_s``: ``GET /optimizaciones/{id}``;
- ``motor_s``: the engine's own duration stored in the run.

The request uses explicit order and vehicle IDs, so no other data in the
database is selected. Each run's rows are deleted afterwards. The client is
in-process (``TestClient``): network latency is not included.

Only for disposable databases whose name ends in ``_test`` or ``_bench``; a
production ``APP_ENV`` is refused. From ``backend/``::

    DATABASE_URL=postgresql+psycopg://...@localhost:5432/ecologistica_bench \\
        python scripts/benchmark_optimizacion.py --corridas 30 \\
        --salida "../docs/03 Implementación/Sprint 04/evidencias/ECL-21/<fecha>"

Writes ``corridas.csv`` and ``resumen.json``; prints the summary. The synthetic
Operator's password is random, used once and never written anywhere.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import secrets
import statistics
import subprocess
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import UUID

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from scripts._guard import ensure_safe_target  # noqa: E402

SUFIJOS = ("_test", "_bench")
LIMITE_RNF001_S = 45.0
CORRIDAS_RNF001 = 30
FECHA = date(2026, 11, 16)  # synthetic operating day; IDs isolate each run
VERSION_BENCH = "BENCH-REFERENCIA-RN"
CAMPOS = (
    "corrida",
    "semilla",
    "estado_http",
    "post_s",
    "detalle_s",
    "total_s",
    "motor_s",
    "rutas",
    "servidos",
    "no_asignados",
    "motivos",
    "distancia_km",
    "secuencial_km",
    "ahorro_distancia_pct",
    "cumplimiento_ventanas_pct",
    "parametros_version",
    "violaciones",
)


# --- pure helpers (unit tested) ----------------------------------------------


def percentil(valores: Sequence[float], p: float) -> float:
    """Nearest-rank percentile, the conservative definition (as in ST-044)."""
    if not valores:
        raise ValueError("Sin valores")
    ordenados = sorted(valores)
    rango = max(1, -(-p * len(ordenados) // 100))
    return ordenados[int(rango) - 1]


def violaciones(detalle: dict[str, Any], capacidades: dict[str, float]) -> list[str]:
    """Hard constraints read back from the API answer: windows, capacity, and
    each selected order served at most once and never also unassigned."""
    problemas = []
    vistos: Counter[str] = Counter()
    for ruta in detalle["rutas"]:
        vehiculo = ruta["vehiculo"]["vehiculo_id"]
        if ruta["peso_kg"] > capacidades.get(vehiculo, 0) + 1e-9:
            problemas.append(f"capacidad:{vehiculo}")
        for parada in ruta["paradas"]:
            vistos[parada["pedido_id"]] += 1
            eta = datetime.fromisoformat(parada["eta"])
            inicio = datetime.fromisoformat(parada["ventana_inicio"])
            fin = datetime.fromisoformat(parada["ventana_fin"])
            if not inicio <= eta <= fin:
                problemas.append(f"ventana:{parada['pedido_id']}")
    problemas += [f"duplicado:{p}" for p, n in vistos.items() if n > 1]
    omitidos = {n["pedido_id"] for n in detalle["no_asignados"]}
    problemas += [f"servido_y_omitido:{p}" for p in omitidos & set(vistos)]
    return problemas


def resumir(filas: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Campaign summary. Failed runs count against RNF-001, never dropped."""
    exitosas = [f for f in filas if f["estado_http"] == 201]
    resumen: dict[str, Any] = {
        "corridas": len(filas),
        "exitosas": len(exitosas),
        "fallidas": len(filas) - len(exitosas),
        "con_violaciones": sum(1 for f in exitosas if f["violaciones"]),
    }
    if not exitosas:
        return {**resumen, "cumple_rnf001": False}
    for campo in ("post_s", "total_s", "motor_s"):
        valores = [f[campo] for f in exitosas]
        resumen[campo] = {
            "min": min(valores),
            "p50": percentil(valores, 50),
            "p95": percentil(valores, 95),
            "max": max(valores),
            "media": statistics.fmean(valores),
        }
    resumen["servidos_min"] = min(f["servidos"] for f in exitosas)
    resumen["no_asignados_max"] = max(f["no_asignados"] for f in exitosas)
    resumen["cumple_rnf001"] = (
        len(filas) >= CORRIDAS_RNF001
        and resumen["fallidas"] == 0
        and resumen["con_violaciones"] == 0
        and resumen["post_s"]["p95"] <= LIMITE_RNF001_S
    )
    return resumen


# --- database and HTTP (run against a disposable database) --------------------


def _sembrar(factory, semilla: int, pedidos: int, vehiculos: int, corrida: int):
    from app.models import Cliente, Pedido, Vehiculo
    from app.optimizacion import sinteticos
    from app.services.optimizaciones import medianoche

    problema = sinteticos.escenario(pedidos, vehiculos, semilla=semilla)
    base = medianoche(FECHA)
    with factory.begin() as session:
        cliente = Cliente(nombre=f"Cliente benchmark {corrida:02d}")
        session.add(cliente)
        session.flush()
        flota = [
            Vehiculo(
                placa=f"BN{corrida:02d}-{i:03d}",
                tipo=v.vehiculo_id.split("-")[1],
                capacidad_kg=Decimal(str(v.capacidad_kg)),
                capacidad_m3=Decimal(str(v.capacidad_m3)),
                rendimiento_km_l=Decimal(str(v.rendimiento_km_l)),
                factor_co2_kg_km=Decimal(str(v.factor_co2_kg_km)),
                anio_fabricacion=2022,
            )
            for i, v in enumerate(problema.vehiculos)
        ]
        filas = [
            Pedido(
                cliente_id=cliente.cliente_id,
                direccion=f"Calle sintética {i}",
                ubicacion=(
                    f"SRID=4326;POINT({p.ubicacion.longitud} {p.ubicacion.latitud})"
                ),
                peso_kg=Decimal(str(p.peso_kg)),
                volumen_m3=Decimal(str(p.volumen_m3)),
                ventana_inicio=base + timedelta(minutes=p.ventana_inicio_min),
                ventana_fin=base + timedelta(minutes=p.ventana_fin_min),
                prioridad=p.prioridad.value,
                tipo_producto="GENERAL",
            )
            for i, p in enumerate(problema.pedidos)
        ]
        session.add_all([*flota, *filas])
        session.flush()
        return (
            cliente.cliente_id,
            [p.pedido_id for p in filas],
            {str(v.vehiculo_id): float(v.capacidad_kg) for v in flota},
        )


def _limpiar(factory, cliente_id: UUID, pedido_ids, vehiculo_ids, run_id) -> None:
    from sqlalchemy import delete

    from app.models import (
        Cliente,
        Optimizacion,
        ParadaRuta,
        Pedido,
        PedidoNoAsignado,
        Ruta,
        Vehiculo,
    )

    with factory.begin() as session:
        if run_id is not None:
            for modelo in (PedidoNoAsignado, ParadaRuta, Ruta):
                session.execute(delete(modelo).where(modelo.optimizacion_id == run_id))
            session.execute(
                delete(Optimizacion).where(Optimizacion.optimizacion_id == run_id)
            )
        session.execute(delete(Pedido).where(Pedido.pedido_id.in_(pedido_ids)))
        session.execute(delete(Vehiculo).where(Vehiculo.vehiculo_id.in_(vehiculo_ids)))
        session.execute(delete(Cliente).where(Cliente.cliente_id == cliente_id))


def _parametros_vigentes(factory, admin_id: UUID) -> tuple[str, bool]:
    """Version in force, registering the RN-011/RN-012 reference if none."""
    from app.core.parametros import REFERENCIA_INICIAL, UNIDADES
    from app.schemas.parametro import ValorParametro, VersionCreate
    from app.services.parametros import ParametroService, ParametrosNoEncontrados

    servicio = ParametroService(factory)
    try:
        return servicio.vigente().version, False
    except ParametrosNoEncontrados:
        pass
    servicio.registrar(
        VersionCreate(
            version=VERSION_BENCH,
            vigente_desde=datetime(2026, 11, 1, 5, 0, tzinfo=timezone.utc),
            nota="EN-003: referencia RN-011/RN-012 para el benchmark.",
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
        admin_id,
    )
    return VERSION_BENCH, True


def _usuario(factory, rol: str, password: str) -> tuple[UUID, str]:
    from app.repositories.usuarios import UsuarioRepository
    from app.services.credenciales import CredentialService

    correo = f"benchmark-{rol.lower()}-{secrets.token_hex(4)}@example.test"
    with factory.begin() as session:
        usuario = CredentialService(UsuarioRepository(session)).create(
            correo, password, rol
        )
    return usuario.usuario_id, correo


def _entorno() -> dict[str, Any]:
    import ortools

    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=BACKEND,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    return {
        "commit": commit,
        "python": platform.python_version(),
        "ortools": ortools.__version__,
        "sistema": f"{platform.system()} {platform.release()}",
        "procesador": platform.processor() or platform.machine(),
        "cpus": os.cpu_count(),
    }


def ejecutar(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corridas", type=int, default=CORRIDAS_RNF001)
    parser.add_argument("--semilla-base", type=int, default=2026)
    parser.add_argument("--pedidos", type=int, default=150)
    parser.add_argument("--vehiculos", type=int, default=15)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    ensure_safe_target(database_url, os.environ.get("APP_ENV"), SUFIJOS)

    from fastapi.testclient import TestClient
    from sqlalchemy import text

    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from app.core.config import Settings
    from app.db.session import build_engine, session_factory
    from app.main import create_app

    settings = Settings(database_url=database_url)
    engine = build_engine(settings)
    head = ScriptDirectory.from_config(
        Config(str(BACKEND / "alembic.ini"))
    ).get_current_head()
    with engine.connect() as conexion:
        actual = conexion.scalar(text("SELECT version_num FROM alembic_version"))
    if actual != head:
        print("La base no está en la última migración; ejecuta alembic upgrade head.")
        return 2
    factory = session_factory(engine)

    password = secrets.token_urlsafe(24)
    admin_id, _ = _usuario(factory, "ADMINISTRADOR", password)
    version, registrada = _parametros_vigentes(factory, admin_id)
    _, correo = _usuario(factory, "OPERADOR", password)

    filas: list[dict[str, Any]] = []
    with TestClient(create_app(settings)) as client:
        login = client.post("/login", json={"email": correo, "password": password})
        del password
        if login.status_code != 200:
            print("No se pudo iniciar sesión con el Operador sintético.")
            return 2
        for corrida in range(1, args.corridas + 1):
            semilla = args.semilla_base + corrida
            cliente_id, pedido_ids, capacidades = _sembrar(
                factory, semilla, args.pedidos, args.vehiculos, corrida
            )
            cuerpo = {
                "fecha_operacion": FECHA.isoformat(),
                "pedido_ids": [str(p) for p in pedido_ids],
                "vehiculo_ids": list(capacidades),
            }
            inicio = perf_counter()
            respuesta = client.post("/optimizaciones", json=cuerpo)
            post_s = perf_counter() - inicio
            fila: dict[str, Any] = {
                "corrida": corrida,
                "semilla": semilla,
                "estado_http": respuesta.status_code,
                "post_s": post_s,
            }
            run_id = None
            if respuesta.status_code == 201:
                run_id = respuesta.json()["optimizacion_id"]
                inicio = perf_counter()
                detalle = client.get(f"/optimizaciones/{run_id}").json()
                fila["detalle_s"] = perf_counter() - inicio
                resumen = detalle["resumen"]
                motivos = Counter(n["motivo"] for n in detalle["no_asignados"])
                fila |= {
                    "total_s": post_s + fila["detalle_s"],
                    "motor_s": detalle["duracion_s"],
                    "rutas": resumen["rutas"],
                    "servidos": resumen["pedidos_asignados"],
                    "no_asignados": resumen["pedidos_no_asignados"],
                    "motivos": ";".join(f"{k}={v}" for k, v in sorted(motivos.items())),
                    "distancia_km": resumen["optimizada"]["distancia_km"],
                    "secuencial_km": resumen["secuencial"]["distancia_km"],
                    "ahorro_distancia_pct": resumen["ahorro_pct"]["distancia"],
                    "cumplimiento_ventanas_pct": resumen["cumplimiento_ventanas_pct"],
                    "parametros_version": detalle["parametros_version"],
                    "violaciones": ";".join(violaciones(detalle, capacidades)),
                }
            elif respuesta.status_code == 503:
                detalle = respuesta.json().get("detail")
                if isinstance(detalle, dict):
                    run_id = detalle.get("optimizacion_id")
            filas.append(fila)
            _limpiar(
                factory,
                cliente_id,
                pedido_ids,
                [UUID(v) for v in capacidades],
                UUID(run_id) if run_id else None,
            )
            print(
                f"corrida {corrida:02d}/{args.corridas}: HTTP {fila['estado_http']}"
                f" en {post_s:.2f} s"
                + (
                    f", {fila['servidos']} servidos, {fila['no_asignados']} sin asignar"
                    if "servidos" in fila
                    else ""
                ),
                flush=True,
            )

    resumen = resumir(filas)
    resumen |= {
        "escenario": {
            "pedidos": args.pedidos,
            "vehiculos": args.vehiculos,
            "semillas": [args.semilla_base + 1, args.semilla_base + args.corridas],
            "fecha_operacion": FECHA.isoformat(),
            "tiempo_limite_motor_s": settings.optimizacion_tiempo_limite_s,
            "cliente": "TestClient en proceso (sin latencia de red)",
        },
        "parametros_version": version,
        "parametros_registrados_por_el_benchmark": registrada,
        "limite_rnf001_s": LIMITE_RNF001_S,
        "medido_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "entorno": _entorno(),
    }
    args.salida.mkdir(parents=True, exist_ok=True)
    with (args.salida / "corridas.csv").open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows({c: fila.get(c, "") for c in CAMPOS} for fila in filas)
    (args.salida / "resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0 if resumen["cumple_rnf001"] else 1


if __name__ == "__main__":
    raise SystemExit(ejecutar())
