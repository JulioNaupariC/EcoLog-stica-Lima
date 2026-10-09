"""Evidence tampering must not produce a consistent load report."""

import gzip
import hashlib
import json
import shutil

import pytest

from loadtest.analysis import schedule, summarize
from loadtest.audit import audit
from loadtest.consolidate import consolidate
from loadtest.report import badge, number, render


def save(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def compress(path, rows):
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")


@pytest.fixture
def evidence(tmp_path):
    summaries = []
    daily_schedule = schedule(1)
    for name, profile, count in [("daily", "daily", 1000), ("stress1", "stress", 3)]:
        directory = tmp_path / name
        directory.mkdir()
        clients = [f"client{i}" for i in range(100)]
        save(
            directory / "manifest.json",
            {
                "clients": clients,
                "ramp": 1,
                "warm": 1,
                "stable": 3,
                "daily_seconds": 180,
            },
        )
        save(
            directory / "baseline.json",
            {
                "clients": clients,
                "vehicles": [str(i) for i in range(50)],
                "fleet_types": {"CAMIONETA": 20, "FURGON": 20, "MOTO": 10},
                "orders": 0,
                "sessions": 0,
            },
        )
        rows = []
        for index in range(count):
            offset = (
                daily_schedule[index]["day_seconds"] * 180 / 61200
                if profile == "daily"
                else 2 + index
            )
            rows.append(
                {
                    "index": index,
                    "phase": "daily" if profile == "daily" else "stable",
                    "status": 201,
                    "valid": True,
                    "pedido_id": str(index),
                    "cliente_id": clients[index % 100],
                    "reference": str(index),
                    "seconds": 1,
                    "start_offset": offset,
                    "end_offset": offset + 1,
                    "hour": daily_schedule[index]["hour"]
                    if profile == "daily"
                    else None,
                    "scheduled_offset": offset if profile == "daily" else index,
                }
            )
        persisted = {
            row["pedido_id"]: (row["cliente_id"], row["reference"]) for row in rows
        }
        compress(directory / "requests.jsonl.gz", rows)
        compress(directory / "persisted.jsonl.gz", rows)
        summary = summarize(rows, persisted)
        summary.update(
            {
                "run": name,
                "profile": profile,
                "total_persisted_all_phases": count,
                "concurrency": {
                    "expected_seconds": 3,
                    "minimum": 99,
                    "maximum": 100,
                    "seconds_at_least_100": 1,
                    "percent_seconds_at_least_100": 100 / 3,
                    "missing_seconds": 1,
                    "sustained_100_pass": False,
                },
                "generator": {
                    "max_scheduler_lag_seconds": 2,
                    "max_cpu_percent_one_core_basis": 20,
                },
                "availability": {
                    "samples": 2,
                    "available": 1,
                    "unavailable": 1,
                    "estimated_missing_slots": 1,
                    "successful_samples_percent": 50,
                    "first_utc": "2026-10-09T09:00:00+00:00",
                    "last_utc": "2026-10-09T09:00:02+00:00",
                },
            }
        )
        summaries.append(summary)
        (directory / "monitor.jsonl").write_text(
            json.dumps({"stable_offset": 1, "inflight": 99}) + "\n"
        )
        (directory / "availability.jsonl").write_text(
            json.dumps({"timestamp": "2026-10-09T09:00:00+00:00", "state": "AVAILABLE"})
            + "\n"
            + json.dumps(
                {"timestamp": "2026-10-09T09:00:02+00:00", "state": "AVAILABLE"}
            )
            + "\n"
        )
    save(
        tmp_path / "campaign.json",
        {
            "results": summaries,
            "aggregate_stress_p95_seconds": 1,
            "aggregate_population": 3,
            "monthly_sla": "NOT_MEASURED",
        },
    )
    save(
        tmp_path / "environment.json",
        {
            "started_utc": "2026-10-09T09:00:00+00:00",
            "platform": "<script>unsafe</script>",
            "logical_cpus": 2,
            "ram_bytes": 1024**3,
            "python": "3.12.6",
            "git_base": "test",
            "packages": {"locust": "2.46.7"},
            "parameters": {"users": 100, "repetitions": 1, "daily_seconds": 180},
        },
    )
    return tmp_path


def test_offline_audit_recalculates_complete_export(evidence):
    result = audit(evidence)
    assert result["evidence_consistent"]
    assert all(result["checks"].values())
    assert result["availability_slots"]["stress1"]["missing_slots"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("aggregate_stress_p95_seconds", 0.1),
        ("aggregate_population", 999),
        ("monthly_sla", "99.5%"),
    ],
)
def test_audit_rejects_altered_campaign_claims(evidence, field, value):
    path = evidence / "campaign.json"
    content = json.loads(path.read_text())
    content[field] = value
    save(path, content)
    assert not audit(evidence)["evidence_consistent"]


def test_audit_rejects_altered_http_counts(evidence):
    path = evidence / "campaign.json"
    content = json.loads(path.read_text())
    content["results"][1]["http_5xx"] = 3
    save(path, content)
    assert not audit(evidence)["checks"]["stress1:summary_matches_raw"]


def test_audit_rejects_missing_schedule_mark(evidence):
    path = evidence / "daily" / "requests.jsonl.gz"
    with gzip.open(path, "rt") as stream:
        rows = [json.loads(line) for line in stream]
    rows[0]["scheduled_offset"] = None
    compress(path, rows)
    assert not audit(evidence)["checks"]["daily:scheduled_and_actual_marks"]


def test_interrupted_window_must_be_declared_invalid(evidence):
    path = evidence / "stress1" / "requests.jsonl.gz"
    with gzip.open(path, "rt") as stream:
        rows = [json.loads(line) for line in stream]
    for row in rows:
        row["start_offset"] += 100000
        row["end_offset"] += 100000
    compress(path, rows)
    summary_path = evidence / "campaign.json"
    content = json.loads(summary_path.read_text())
    content["results"][1]["load_acceptance_pass"] = False
    save(summary_path, content)
    assert audit(evidence)["evidence_consistent"]
    content["results"][1]["load_acceptance_pass"] = True
    save(summary_path, content)
    assert not audit(evidence)["checks"]["stress1:stable_window_or_declared_invalid"]


def test_audit_checks_file_integrity(evidence):
    path = evidence / "environment.json"
    save(
        evidence / "sha256.json",
        {"environment.json": hashlib.sha256(path.read_bytes()).hexdigest()},
    )
    assert audit(evidence)["checks"]["files:sha256"]
    path.write_text("{}")
    assert not audit(evidence)["checks"]["files:sha256"]


def test_report_keeps_failures_scope_and_escaped_environment(evidence):
    audit(evidence)
    target = render(evidence)
    content = target.read_text(encoding="utf-8")
    assert "NO ACREDITADO" in content
    assert "SLA mensual: NO MEDIDO" in content
    assert "&lt;script&gt;unsafe&lt;/script&gt;" in content
    assert "<script>unsafe</script>" not in content
    assert "Huecos estimados" in content
    assert "Agregado diagnóstico" in content
    assert "99" in content


def test_no_data_is_not_presented_as_zero():
    assert number(None) == "Sin datos"
    assert number(0) == "0.000"
    assert "CUMPLE" in badge(True)
    assert "NO ACREDITADO" in badge(False)


def recovery_fixture(evidence, tmp_path):
    original = json.loads((evidence / "campaign.json").read_text())
    prototype = original["results"][1]
    prototype["load_acceptance_pass"] = False
    original["results"][0]["load_acceptance_pass"] = True
    for name in ("stress2", "stress3"):
        shutil.copytree(evidence / "stress1", evidence / name)
        original["results"].append(dict(prototype, run=name))
    recovery = tmp_path / "recovery"
    recovery.mkdir()
    shutil.copytree(evidence / "stress1", recovery / "stress2")
    save(recovery / "campaign.json", {"results": [dict(prototype, run="stress2")]})
    for directory in [evidence / "stress1", evidence / "stress3", recovery / "stress2"]:
        manifest = json.loads((directory / "manifest.json").read_text())
        manifest.update(ramp=60, warm=120, stable=600)
        save(directory / "manifest.json", manifest)
        (directory / "monitor.jsonl").write_text(
            json.dumps({"event": "end", "elapsed_seconds": 780.1}) + "\n"
        )
        path = directory / "requests.jsonl.gz"
        with gzip.open(path, "rt") as stream:
            rows = [json.loads(line) for line in stream]
        for row in rows:
            row["start_offset"] += 198
            row["end_offset"] += 198
        compress(path, rows)
    save(evidence / "campaign.json", original)
    return recovery


def test_recovery_preserves_native_exports_and_uses_three_complete_windows(
    evidence, tmp_path
):
    recovery = recovery_fixture(evidence, tmp_path)
    original_bytes = (evidence / "campaign.json").read_bytes()
    result = json.loads(consolidate(evidence, recovery).read_text())
    assert (evidence / "campaign.json").read_bytes() == original_bytes
    assert result["aggregate_population"] == 9
    assert result["aggregate_stress_p95_seconds"] == 1
    assert result["completed_stress_windows"] == 3
    assert result["all_load_profiles_pass"] is False
    assert result["results"][2]["include_in_aggregate"] is False
    assert audit(evidence)["evidence_consistent"]
    assert "stress2 (recuperación)" in render(evidence).read_text(encoding="utf-8")


def test_recovery_rejects_short_or_interrupted_window(evidence, tmp_path):
    recovery = recovery_fixture(evidence, tmp_path)
    (recovery / "stress2" / "monitor.jsonl").write_text(
        json.dumps({"event": "end", "elapsed_seconds": 24000}) + "\n"
    )
    with pytest.raises(ValueError, match="interrupted or shortened"):
        consolidate(evidence, recovery)


def test_recovery_rejects_multiple_profiles(evidence, tmp_path):
    recovery = recovery_fixture(evidence, tmp_path)
    content = json.loads((recovery / "campaign.json").read_text())
    content["results"] *= 2
    save(recovery / "campaign.json", content)
    with pytest.raises(ValueError, match="one stress profile"):
        consolidate(evidence, recovery)
