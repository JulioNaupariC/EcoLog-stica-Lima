"""Recalculate the baseline from original reports and API CSVs, without writes."""

import csv
import json
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parent
FIELDS = {
    "fcp_ms": "first-contentful-paint",
    "lcp_ms": "largest-contentful-paint",
    "tbt_ms": "total-blocking-time",
    "cls": "cumulative-layout-shift",
}

for name in ("login", "itinerario-conductor"):
    samples = []
    for number in range(1, 4):
        prefix = f"{name}-{number:02}"
        report = json.loads((ROOT / f"{prefix}.lighthouse.json").read_text("utf-8"))
        network = json.loads((ROOT / f"{prefix}.network.json").read_text("utf-8"))
        assert not report.get("runtimeError")
        assert network["cacheDisabled"]
        assert network["finalUrl"].endswith("/login" if name == "login" else "/conductor/itinerario")
        sample = {key: report["audits"][audit]["numericValue"] for key, audit in FIELDS.items()}
        sample.update(performance=report["categories"]["performance"]["score"] * 100,
                      bytes=network["transferredBytes"], requests=network["requests"])
        samples.append(sample)
    print(name, json.dumps({key: median(s[key] for s in samples) for key in samples[0]}))

for name in ("vehiculos", "conductores", "incidencias"):
    with (ROOT / f"api-{name}.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 20
    assert all(row["status"] == "200" for row in rows)
    assert all(row["content_encoding"] == "identity" for row in rows)
    print(name, json.dumps({"samples": len(rows),
          "mean_ms": mean(float(row["duration_ms"]) for row in rows),
          "mean_body_bytes": mean(int(row["body_bytes"]) for row in rows)}))

print("OK: 6 Lighthouse reports, 6 Network records and 60 HTTP 200 samples verified.")
