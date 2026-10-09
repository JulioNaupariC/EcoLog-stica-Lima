"""Capture local HTTP metric evidence without exporting credentials or business data."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from app.monitoring.poll import sample


def verify_failures(output: Path) -> dict[str, object]:
    """Use a separate in-process API; never break the running preview service."""
    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.main import create_app
    from app.monitoring.probe import build_probe_engine

    app = create_app(Settings())

    @app.get("/ecl60-controlled-error")
    def controlled_error() -> None:
        raise RuntimeError("controlled synthetic failure")

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/health/ready").status_code == 200
        original = app.state.probe_engine
        target = original.url.set(host="127.0.0.1", port=1)
        unreachable = build_probe_engine(
            Settings(database_url=target.render_as_string(hide_password=False))
        )
        try:
            app.state.probe_engine = unreachable
            assert client.get("/health").status_code == 200
            failed = client.get("/health/ready")
            assert failed.status_code == 503
            assert failed.json()["database"] == "down"
            assert failed.json()["database_latency_seconds"] <= 5
        finally:
            app.state.probe_engine = original
            unreachable.dispose()
        assert client.get("/health/ready").status_code == 200
        assert client.get("/ecl60-controlled-error").status_code == 500
        snapshot = app.state.metrics.render()
        assert 'ecolog_http_5xx_total{method="GET",route="/health/ready"} 1' in snapshot
        assert (
            'ecolog_http_5xx_total{method="GET",route="/ecl60-controlled-error"} 1'
            in snapshot
        )
        assert "ecolog_database_up 1" in snapshot
        (output / "metricas-fallos-controlados.prom").write_text(
            snapshot, encoding="utf-8"
        )
    return {
        "separate_in_process_api": True,
        "database_connection_refused": 503,
        "process_liveness_during_db_failure": 200,
        "database_recovered": 200,
        "controlled_unhandled_exception": 500,
        "five_xx_counted": True,
    }


def main() -> int:
    base = os.environ.get("MONITORING_TEST_URL", "http://127.0.0.1:8001").rstrip("/")
    origin = urlsplit(base)
    if (
        origin.scheme not in {"http", "https"}
        or origin.hostname not in {"127.0.0.1", "localhost"}
        or origin.username
        or origin.password
        or origin.path
        or origin.query
        or origin.fragment
    ):
        raise SystemExit("This evidence script only targets a local test API")
    email = os.environ["MONITORING_TEST_EMAIL"]
    password = os.environ["MONITORING_TEST_PASSWORD"]
    output = Path(__file__).resolve().parents[1] / "evidencias/ECL-60"
    output.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=base, timeout=5) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health/ready").status_code == 200
        assert client.get("/metrics").status_code == 401
        assert (
            client.post(
                "/login", json={"email": email, "password": password}
            ).status_code
            == 200
        )
        assert client.get("/conductores").status_code == 200
        text = client.get("/metrics").raise_for_status().text
        assert (
            'ecolog_http_requests_total{method="GET",route="/health",status="200"}'
            in text
        )
        assert 'engine="business",operation="SELECT",outcome="success"}' in text
        assert "ecolog_database_up 1" in text
        assert email not in text and password not in text
        (output / "metricas.prom").write_text(text, encoding="utf-8")
        samples = [sample(base), sample(base)]
        assert all(item["state"] == "AVAILABLE" for item in samples)
        (output / "sondeos.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in samples), encoding="utf-8"
        )
        assert client.post("/logout").status_code == 204
    controlled = verify_failures(output)
    results = {
        "controlled_failures": controlled,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base,
        "environment": "local synthetic preview, PostgreSQL 16/PostGIS Docker",
        "real_http": True,
        "health": 200,
        "ready": 200,
        "unauthenticated_metrics": 401,
        "authenticated_metrics": 200,
        "business_sql_observed": True,
        "available_samples": len(samples),
        "sampling": "two immediate smoke observations; not a 60-second campaign",
        "sla_monthly_verified": False,
        "capacity_campaign_executed": False,
    }
    (output / "resultados.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "Local HTTP metrics and availability evidence passed; no credentials exported"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
