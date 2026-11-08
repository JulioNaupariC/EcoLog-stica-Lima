"""Recalcula medianas y deltas desde JSON/CSV originales, sin modificarlos.

Uso: python comparar.py RUN_PRINCIPAL RUN_SIN_SW [--write]
--write crea comparacion.md y comparacion.json una sola vez junto al script.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "antes/run-2026-11-06T23-50-12-524Z"
PAGES = {
    "login": "/login",
    "inicio-operador": "/",
    "vehiculos-operador": "/vehiculos",
    "itinerario-conductor": "/conductor/itinerario",
}
AUDITS = {
    "FCP ms": "first-contentful-paint",
    "LCP ms": "largest-contentful-paint",
    "TBT ms": "total-blocking-time",
    "CLS": "cumulative-layout-shift",
}
LIMITS = {"Performance /100": 90, "FCP ms": 1000, "LCP ms": 1400,
          "TBT ms": 85, "CLS": 0.02, "Transferido bytes": 1_100_000}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def page_metrics(directory: Path, name: str) -> dict | None:
    record = read(directory / f"{name}.resultado.json")
    if record["status"] == "NO_MEDIBLE":
        assert not record["rounds"]
        return None
    assert record["status"] == "MEDIDO", (directory, name, record["status"])
    assert len(record["rounds"]) == 3
    samples = []
    for number in range(1, 4):
        prefix = f"{name}-{number:02}"
        report = read(directory / f"{prefix}.lighthouse.json")
        network = read(directory / f"{prefix}.network.json")
        assert not report.get("runtimeError")
        assert report["lighthouseVersion"] == "12.8.2"
        assert report["finalDisplayedUrl"] == f"http://127.0.0.1:5173{PAGES[name]}"
        assert network["finalUrl"] == report["finalDisplayedUrl"]
        assert network["cacheDisabled"] and network["failures"] == 0
        baseline = read(BASE / "login-01.lighthouse.json")["configSettings"]
        for key in ("formFactor", "screenEmulation", "throttling",
                    "throttlingMethod", "disableStorageReset", "onlyCategories"):
            assert report["configSettings"][key] == baseline[key], key
        samples.append({
            "Performance /100": report["categories"]["performance"]["score"] * 100,
            **{key: report["audits"][audit]["numericValue"] for key, audit in AUDITS.items()},
            "Transferido bytes": network["transferredBytes"],
            "Peticiones": network["requests"],
        })
    return {key: median(row[key] for row in samples) for key in samples[0]}


def api_metrics(directory: Path, name: str) -> dict:
    with (directory / f"api-{name}.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 20
    assert [int(row["sample"]) for row in rows] == list(range(1, 21))
    assert all(row["status"] == "200" and row["content_encoding"] == "identity" for row in rows)
    return {"Media ms": mean(float(row["duration_ms"]) for row in rows),
            "Media bytes cuerpo": mean(int(row["body_bytes"]) for row in rows),
            "Min bytes": min(int(row["body_bytes"]) for row in rows),
            "Max bytes": max(int(row["body_bytes"]) for row in rows)}


def delta(before: float, after: float) -> dict:
    return {"antes": before, "despues": after, "delta": after - before,
            "porcentaje": (after - before) / before * 100 if before else None}


def fmt(value: float | None) -> str:
    if value is None:
        return "N/A (base cero)"
    return f"{value:.9f}".rstrip("0").rstrip(".")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    primary, supplement = (Path(arg).resolve() for arg in sys.argv[1:3])
    result: dict = {"baseline": str(BASE.relative_to(ROOT.parent)),
                    "principal": primary.name, "sin_service_worker": supplement.name,
                    "pages": {}, "api": {}}
    lines = ["# ECL-115 — Comparación reproducible ANTES vs. DESPUÉS", "",
             "Δ = DESPUÉS − ANTES; Δ% = 100 × Δ / ANTES. Base cero: porcentaje indefinido.",
             "Mediana independiente de cada métrica de tres corridas. MB decimal (1,1 MB = 1 100 000 bytes).",
             "NM = no medible; nunca se sustituye por cero. API: media de 20 respuestas HTTP 200.", "",
             "Producción cambia el modo de servicio respecto a Vite desarrollo. La campaña principal conserva",
             "el procedimiento original y reutiliza Cache Storage del service worker. La suplementaria",
             "evita el service worker: es otro escenario, no una repetición exacta ni una primera visita con precarga.", ""]
    for name, path in PAGES.items():
        # The baseline's operator diagnosis was repeated in a separate final run.
        before_directory = (BASE.parent / "run-2026-11-06T23-56-10-225Z"
                            if name in ("inicio-operador", "vehiculos-operador") else BASE)
        before = page_metrics(before_directory, name)
        after = page_metrics(primary, name)
        cold = page_metrics(supplement, name) if name in ("login", "itinerario-conductor") else None
        result["pages"][name] = {"path": path, "antes": before, "principal": after,
                                "sin_sw": cold, "deltas_principal": {}, "deltas_sin_sw": {}}
        lines.extend([f"## `{path}`", "",
                      "| Métrica | ANTES | DESPUÉS principal | Δ | Δ% | DESPUÉS sin SW | Δ sin SW | Δ% sin SW |",
                      "|---|---:|---:|---:|---:|---:|---:|---:|"])
        if before is None or after is None:
            lines.extend(["| Todas | NM | NM | N/A | N/A | NM | N/A | N/A |", "",
                          "La recarga completa redirige a login; no hay tres corridas válidas de esta vista.", ""])
            continue
        for key in before:
            d = delta(before[key], after[key])
            c = delta(before[key], cold[key])
            result["pages"][name]["deltas_principal"][key] = d
            result["pages"][name]["deltas_sin_sw"][key] = c
            lines.append(f"| {key} | {fmt(d['antes'])} | {fmt(d['despues'])} | {fmt(d['delta'])} | {fmt(d['porcentaje'])} | {fmt(c['despues'])} | {fmt(c['delta'])} | {fmt(c['porcentaje'])} |")
        lines.extend(["", "| Umbral | Principal | Sin SW |", "|---|---|---|"])
        for key, limit in LIMITS.items():
            def verdict(metrics: dict) -> str:
                ok = metrics[key] >= limit if key == "Performance /100" else metrics[key] <= limit
                return "Cumple" if ok else "NO cumple"
            lines.append(f"| {key}: {'≥' if key == 'Performance /100' else '≤'} {limit} | {verdict(after)} | {verdict(cold)} |")
        lines.append("")
    lines.extend(["## API (Accept-Encoding: identity)", "",
                  "| Endpoint | Métrica | ANTES | DESPUÉS | Δ | Δ% |",
                  "|---|---|---:|---:|---:|---:|"])
    for name, endpoint in (("vehiculos", "/vehiculos"), ("conductores", "/conductores?page=1"), ("incidencias", "/incidencias?page=1")):
        before, after = api_metrics(BASE, name), api_metrics(primary, name)
        result["api"][endpoint] = {key: delta(before[key], after[key]) for key in before}
        for key, d in result["api"][endpoint].items():
            lines.append(f"| `{endpoint}` | {key} | {fmt(d['antes'])} | {fmt(d['despues'])} | {fmt(d['delta'])} | {fmt(d['porcentaje'])} |")
    lines.extend(["", "[← Volver al README principal](../../../../../README.md)", ""])
    document = "\n".join(lines)
    if "--write" in sys.argv:
        for filename, data in (("comparacion.md", document), ("comparacion.json", json.dumps(result, ensure_ascii=False, indent=2) + "\n")):
            with (ROOT / filename).open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(data)
    print(document)
    print("OK: medianas, configuración Lighthouse, Network y 120 muestras API verificadas.")


if __name__ == "__main__":
    main()
