"""Recalculate exported results offline; no API or database connections."""

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

from loadtest.analysis import HOURLY, availability_slots, percentile, summarize


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_gzip(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def audit(directory: Path) -> dict:
    consolidated = directory / "campaign-consolidated.json"
    campaign = read_json(
        consolidated if consolidated.exists() else directory / "campaign.json"
    )
    checks: dict[str, bool] = {}
    durations = []
    availability = {}
    daily_timing = {}
    for expected in campaign["results"]:
        name = expected["run"]
        profile = directory / expected.get("evidence_directory", name)
        manifest = read_json(profile / "manifest.json")
        baseline = read_json(profile / "baseline.json")
        checks[f"{name}:baseline"] = (
            len(set(baseline["clients"])) == 100
            and len(set(baseline["vehicles"])) == 50
            and baseline["fleet_types"] == {"CAMIONETA": 20, "FURGON": 20, "MOTO": 10}
            and baseline["orders"] == baseline["sessions"] == 0
            and set(baseline["clients"]) == set(manifest["clients"])
        )
        persisted_rows = read_gzip(profile / "persisted.jsonl.gz")
        if (profile / "availability.jsonl").exists():
            observations = [
                json.loads(line)
                for line in (profile / "availability.jsonl").read_text().splitlines()
                if line.startswith("{")
            ]
            availability[name] = availability_slots(observations)
        persisted = {
            row["pedido_id"]: (row["cliente_id"], row["reference"])
            for row in persisted_rows
        }
        attempts = read_gzip(profile / "requests.jsonl.gz")
        checks[f"{name}:unique_attempts"] = len(
            {row["index"] for row in attempts}
        ) == len(attempts)
        checks[f"{name}:unique_persisted"] = len(persisted) == len(persisted_rows)
        checks[f"{name}:monotonic_durations"] = all(
            row["seconds"] >= 0
            and abs(row["end_offset"] - row["start_offset"] - row["seconds"]) < 0.00001
            for row in attempts
        )
        phase = "daily" if expected["profile"] == "daily" else "stable"
        selected = [row for row in attempts if row["phase"] == phase]
        recalculated = summarize(selected, persisted)
        checks[f"{name}:summary_matches_raw"] = all(
            expected[key] == value for key, value in recalculated.items()
        )
        checks[f"{name}:persisted_population"] = (
            len(persisted) == expected["total_persisted_all_phases"]
        )
        if phase == "daily":
            checks["daily:hourly_counts"] = [
                sum(row["hour"] == hour and row["valid"] for row in selected)
                for hour in range(5, 22)
            ] == list(HOURLY)
            checks["daily:scheduled_and_actual_marks"] = all(
                isinstance(row["scheduled_offset"], (int, float))
                and math.isfinite(row["scheduled_offset"])
                and math.isfinite(row["start_offset"])
                for row in selected
            )
            differences = [
                row["start_offset"] - row["scheduled_offset"]
                for row in selected
                if isinstance(row["scheduled_offset"], (int, float))
            ]
            daily_timing = {
                "early_count": sum(value < 0 for value in differences),
                "max_early_seconds": max(0, -min(differences, default=0)),
                "max_late_seconds": max(differences, default=None),
            }
            if "daily_seconds" in manifest:
                checks["daily:actual_hourly_counts"] = [
                    sum(
                        5 + int(row["start_offset"] * 17 / manifest["daily_seconds"])
                        == hour
                        for row in selected
                    )
                    for hour in range(5, 22)
                ] == list(HOURLY)
        else:
            start = manifest["ramp"] + manifest["warm"]
            finish = start + manifest["stable"]
            within_window = all(
                start <= row["start_offset"] < finish for row in selected
            )
            checks[f"{name}:stable_window_or_declared_invalid"] = (
                within_window or expected.get("load_acceptance_pass") is False
            )
            if not expected.get("include_in_aggregate", True):
                continue
            durations.extend(
                row["seconds"]
                for row in selected
                if row["valid"]
                and persisted.get(row["pedido_id"])
                == (row["cliente_id"], row["reference"])
            )
    checks["aggregate:raw_percentile"] = (
        percentile(durations) == campaign["aggregate_stress_p95_seconds"]
    )
    checks["aggregate:population"] = len(durations) == campaign["aggregate_population"]
    checks["scope:no_monthly_sla_claim"] = campaign["monthly_sla"] == "NOT_MEASURED"
    if (directory / "sha256.json").exists():
        checks["files:sha256"] = all(
            (directory / name).is_file()
            and hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest
            for name, digest in read_json(directory / "sha256.json").items()
        )
    result = {
        "evidence_consistent": all(checks.values()),
        "checks": checks,
        "availability_slots": availability,
        "daily_timing": daily_timing,
        "note": "Evidence consistency does not imply performance acceptance.",
    }
    (directory / "audit.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = audit(args.directory.resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["evidence_consistent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
