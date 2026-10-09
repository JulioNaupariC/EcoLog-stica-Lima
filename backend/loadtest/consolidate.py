"""Consolidate an isolated recovery without overwriting native campaign exports."""

import argparse
import json
import os
from pathlib import Path

from loadtest.analysis import percentile
from loadtest.audit import read_gzip, read_json


def consolidate(primary: Path, recovery: Path) -> Path:
    original = read_json(primary / "campaign.json")
    recovered = read_json(recovery / "campaign.json")
    if len(recovered["results"]) != 1:
        raise ValueError("Recovery must contain one stress profile")
    replacement = recovered["results"][0]
    replaced = replacement["run"]
    if replacement["profile"] != "stress":
        raise ValueError("Recovery must be stress")
    results = []
    for row in original["results"]:
        record = dict(row)
        record["evidence_directory"] = record["run"]
        record["include_in_aggregate"] = (
            record["profile"] == "stress" and record["run"] != replaced
        )
        if record["run"] == replaced:
            record["report_label"] = f"{replaced} (interrumpida)"
        results.append(record)
    record = dict(replacement)
    record.update(
        run=f"{replaced}-recovery",
        original_run=replaced,
        evidence_directory=Path(
            os.path.relpath(recovery / replaced, primary)
        ).as_posix(),
        report_label=f"{replaced} (recuperación)",
        include_in_aggregate=True,
    )
    results.append(record)
    durations = []
    completed = []
    for row in results:
        if not row["include_in_aggregate"]:
            continue
        directory = primary / row["evidence_directory"]
        manifest = read_json(directory / "manifest.json")
        monitor = [
            json.loads(line)
            for line in (directory / "monitor.jsonl").read_text().splitlines()
        ]
        ends = [
            item["elapsed_seconds"] for item in monitor if item.get("event") == "end"
        ]
        target = manifest["ramp"] + manifest["warm"] + manifest["stable"]
        if (
            (manifest["ramp"], manifest["warm"], manifest["stable"]) != (60, 120, 600)
            or not ends
            or not target - 1 <= ends[-1] <= target + 20
        ):
            raise ValueError("Selected measurement window was interrupted or shortened")
        persisted = {
            item["pedido_id"]: (item["cliente_id"], item["reference"])
            for item in read_gzip(directory / "persisted.jsonl.gz")
        }
        seen = set()
        for item in read_gzip(directory / "requests.jsonl.gz"):
            if item["phase"] == "stable" and not (
                manifest["ramp"] + manifest["warm"] <= item["start_offset"] < target
            ):
                raise ValueError("Stable request outside planned measurement window")
            if (
                item["phase"] == "stable"
                and item["valid"]
                and item["pedido_id"] not in seen
                and persisted.get(item["pedido_id"])
                == (item["cliente_id"], item["reference"])
            ):
                seen.add(item["pedido_id"])
                durations.append(item["seconds"])
        completed.append(row["run"])
    if len(completed) != 3:
        raise ValueError("Three complete stress measurement windows required")
    content = {
        "results": results,
        "aggregate_stress_p95_seconds": percentile(durations),
        "aggregate_population": len(durations),
        "aggregate_selected_profiles": completed,
        "completed_stress_windows": 3,
        "nominal_timer_tolerance_seconds": 1,
        "recovery_included": True,
        "all_load_profiles_pass": all(
            row["load_acceptance_pass"] for row in results if row["run"] != replaced
        ),
        "methodology_durations_match_plan": True,
        "rnf008_integral": "PENDING_DASHBOARD_ECL15",
        "monthly_sla": "NOT_MEASURED",
        "native_primary": "campaign.json",
        "native_recovery": Path(
            os.path.relpath(recovery / "campaign.json", primary)
        ).as_posix(),
        "note": "Interrupted export retained; recovery replaces aggregate; no SLA.",
    }
    target = primary / "campaign-consolidated.json"
    target.write_text(json.dumps(content, indent=2), encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("primary", type=Path)
    parser.add_argument("recovery", type=Path)
    args = parser.parse_args()
    print(consolidate(args.primary.resolve(), args.recovery.resolve()))


if __name__ == "__main__":
    main()
