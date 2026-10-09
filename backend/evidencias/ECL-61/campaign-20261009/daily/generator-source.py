"""Real authenticated HTTP; launch via python -m loadtest.campaign."""

import gzip
import itertools
import json
import os
import re
import time
from pathlib import Path
from uuid import UUID

import gevent
import psutil
from locust import HttpUser, constant, events, task
from locust.exception import StopUser

CONFIG = json.loads(Path(os.environ["ST035_CONFIG"]).read_text(encoding="utf-8"))
OUT = Path(CONFIG["output"])
COUNTER = itertools.count()
USERS = itertools.count()
START = None
LOG = None
AUX = None
FAILED_SETUP = False


def phase(now):
    if CONFIG["profile"] == "daily":
        return "daily"
    elapsed = now - START
    if elapsed < CONFIG["ramp"]:
        return "ramp"
    if elapsed < CONFIG["ramp"] + CONFIG["warm"]:
        return "warm"
    return "stable"


def payload(index):
    return {
        "cliente_id": CONFIG["clients"][index % len(CONFIG["clients"])],
        "direccion": "Punto sintetico ST035 Lima Este",
        "referencia": f"ST035:{CONFIG['run']}:{index}",
        "latitud": -12.0 + (index % 100) / 10000,
        "longitud": -77.0 + (index % 100) / 10000,
        "peso_kg": "12.50",
        "volumen_m3": "0.080",
        "ventana_inicio": "2026-10-10T09:00:00-05:00",
        "ventana_fin": "2026-10-10T18:00:00-05:00",
        "prioridad": ("ESTANDAR", "EXPRESS", "ECONOMICO")[index % 3],
        "tipo_producto": "SINTETICO",
    }


class Orders(HttpUser):
    wait_time = constant(0)

    def on_start(self):
        global FAILED_SETUP
        self.number = next(USERS)
        response = self.client.post(
            "/login",
            json={
                "email": f"st035-{self.number}@example.test",
                "password": os.environ["ST035_PASSWORD"],
            },
            timeout=5,
            name="setup/login",
        )
        if response.status_code != 200:
            FAILED_SETUP = True
            AUX.write(
                json.dumps({"event": "login_failed", "status": response.status_code})
                + "\n"
            )
            raise StopUser()

    @task
    def register(self):
        index = next(COUNTER)
        planned = None
        hour = None
        if CONFIG["profile"] == "daily":
            if index >= 1000:
                raise StopUser()
            item = CONFIG["schedule"][index]
            planned = START + item["day_seconds"] * CONFIG["daily_seconds"] / 61200
            hour = item["hour"]
            gevent.sleep(max(0, planned - time.perf_counter()))
        body = payload(index)
        started = time.perf_counter()
        epoch = time.time()
        current_phase = phase(started)
        valid = False
        identifier = None
        with self.client.post(
            "/pedidos",
            json=body,
            timeout=10,
            name=f"{current_phase}/POST pedidos",
            catch_response=True,
        ) as response:
            elapsed = time.perf_counter() - started
            status = response.status_code or None
            if status == 201:
                try:
                    result = response.json()
                    identifier = str(UUID(result["pedido_id"]))
                    valid = (
                        result["cliente_id"] == body["cliente_id"]
                        and result["referencia"] == body["referencia"]
                        and result["estado"] == "PENDIENTE"
                    )
                except (ValueError, KeyError, TypeError):
                    pass
            if not valid:
                response.failure("Unexpected status/body or transport failure")
        LOG.write(
            json.dumps(
                {
                    "index": index,
                    "phase": current_phase,
                    "started_epoch": epoch,
                    "start_offset": started - START,
                    "end_offset": started - START + elapsed,
                    "seconds": elapsed,
                    "status": status,
                    "valid": valid,
                    "pedido_id": identifier,
                    "cliente_id": body["cliente_id"],
                    "reference": body["referencia"],
                    "hour": hour,
                    "scheduled_offset": planned - START
                    if planned is not None
                    else None,
                }
            )
            + "\n"
        )


def observe(environment):
    import requests

    process = psutil.Process()
    session = requests.Session()
    login = session.post(
        CONFIG["url"] + "/login",
        json={
            "email": "st035-0@example.test",
            "password": os.environ["ST035_PASSWORD"],
        },
        timeout=5,
    )
    if login.status_code != 200:
        AUX.write(json.dumps({"event": "monitor_login_failed"}) + "\n")
        environment.runner.quit()
        return
    deadline = time.perf_counter()
    while environment.runner.state not in {"stopped", "stopping", "cleanup"}:
        started = time.perf_counter()
        row = {
            "epoch": time.time(),
            "offset": started - START,
            "stable_offset": started - START - CONFIG["ramp"] - CONFIG["warm"],
            "generator_cpu_percent": process.cpu_percent(),
            "generator_rss_bytes": process.memory_info().rss,
            "host_cpu_percent": psutil.cpu_percent(),
            "host_memory_percent": psutil.virtual_memory().percent,
            "scheduler_lag_seconds": max(0, started - deadline),
            "inflight": None,
        }
        try:
            response = session.get(CONFIG["url"] + "/metrics", timeout=5)
            row["metrics_status"] = response.status_code
            if response.status_code == 200:
                expression = (
                    r'ecolog_http_requests_in_flight\{method="POST",'
                    r'route="/pedidos"\} (\d+)'
                )
                match = re.search(expression, response.text)
                row["inflight"] = int(match[1]) if match else None
                if int(started - START) % 60 == 0:
                    (OUT / f"metrics-{int(started - START):04}.prom").write_text(
                        response.text
                    )
        except requests.RequestException:
            row["metrics_status"] = None
        row["scrape_seconds"] = time.perf_counter() - started
        AUX.write(json.dumps(row) + "\n")
        AUX.flush()
        deadline += 1
        gevent.sleep(max(0, deadline - time.perf_counter()))


@events.test_start.add_listener
def start(environment, **kwargs):
    global START, LOG, AUX
    START = time.perf_counter()
    LOG = gzip.open(OUT / "requests.jsonl.gz", "wt", encoding="utf-8")
    AUX = (OUT / "monitor.jsonl").open("w", encoding="utf-8")
    gevent.spawn(observe, environment)


@events.test_stop.add_listener
def stop(environment, **kwargs):
    LOG.close()
    AUX.write(
        json.dumps(
            {
                "event": "end",
                "setup_failed": FAILED_SETUP,
                "elapsed_seconds": time.perf_counter() - START,
            }
        )
        + "\n"
    )
    AUX.close()
