"""Energy and CO2e per visit with the Sustainable Web Design Model v4 (ECL-116).

Green IT, Inspección 4, criterion 1. Turns the bytes measured by ECL-108
(ANTES) and ECL-115 (DESPUÉS) into kWh and grams of CO2e per visit, plus an
annual projection under an explicit, adjustable visits assumption.

Sources, consulted on 06/11/2026:

* SWDM v4 coefficients and formula:
  https://sustainablewebdesign.org/estimating-digital-emissions/
* Reference implementation used to cross-check every number (same
  coefficients, ratings and formula): CO2.js 0.19.0 by The Green Web
  Foundation, ``@tgwf/co2`` on npm, published 29/06/2026.
* Peru grid intensity (operational segments only, as SWDM v4 recommends):
  Ember annual average included in CO2.js 0.19.0 (``PER``) and, as a
  sensitivity check, Electricity Maps 2025 for Peru (``PE``), also in CO2.js.
  An official SEIN factor (COES/MINEM) has not been sourced; it is not used.

Units: 1 GB = 10^9 bytes (decimal), as SWDM v4 and CO2.js use. Bytes are the
"Transferred" total of a full page load with the cache disabled.

Usage, from ``backend/``::

    python scripts/swdm_v4.py
    python scripts/swdm_v4.py --despues "<ruta>/resultados.json"
    python scripts/swdm_v4.py --bytes 1100000 --visitas-anuales 10000
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median

BYTES_PER_GB = 1_000_000_000

# SWDM v4 energy intensities, kWh per GB transferred.
OPERATIONAL_KWH_PER_GB = {"data_center": 0.055, "network": 0.059, "device": 0.080}
EMBODIED_KWH_PER_GB = {"data_center": 0.012, "network": 0.013, "device": 0.081}
KWH_PER_GB = sum(OPERATIONAL_KWH_PER_GB.values()) + sum(EMBODIED_KWH_PER_GB.values())

# Grid carbon intensities, g CO2e per kWh.
GLOBAL_GRID_G_PER_KWH = 494.0  # SWDM v4 global average (Ember, World).
PERU_EMBER_G_PER_KWH = 263.27  # CO2.js 0.19.0, average-intensities "PER".
PERU_ELECTRICITY_MAPS_2025_G_PER_KWH = 173.0  # CO2.js 0.19.0, yearly_2025 "PE".

# SWDM v4 digital carbon rating, upper bound in g CO2e per page view.
RATINGS = (
    ("A+", 0.040),
    ("A", 0.079),
    ("B", 0.145),
    ("C", 0.209),
    ("D", 0.278),
    ("E", 0.359),
)

# Annual projection: an assumption, not company data. One itinerary load per
# vehicle and working day in the case's 15-vehicle scenario (RNF-001),
# 300 working days a year. Change it with --visitas-anuales.
VEHICULOS_ESCENARIO = 15
CARGAS_POR_JORNADA = 1
JORNADAS_POR_ANIO = 300
VISITAS_ANUALES_SUPUESTAS = VEHICULOS_ESCENARIO * CARGAS_POR_JORNADA * JORNADAS_POR_ANIO

EVIDENCIAS = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "03 Implementación"
    / "reduccion del impacto ambiental"
    / "evidencias"
)
ANTES_RESULTADOS = (
    EVIDENCIAS / "antes" / "run-2026-11-06T23-50-12-524Z" / "resultados.json"
)


@dataclass(frozen=True)
class Visita:
    """SWDM v4 result for one page view."""

    bytes: int
    kwh: float
    g_co2e: float
    g_co2e_peru: float
    rating: str


def rating(g_co2e: float) -> str:
    for grade, upper in RATINGS:
        if g_co2e <= upper:
            return grade
    return "F"


def energia_kwh(transferred_bytes: float) -> float:
    """Total SWDM v4 energy (operational + embodied) for the bytes."""
    return transferred_bytes / BYTES_PER_GB * KWH_PER_GB


def emisiones_g(
    transferred_bytes: float,
    grid_g_per_kwh: float = GLOBAL_GRID_G_PER_KWH,
    green_hosting_factor: float = 0.0,
    new_visitor_ratio: float = 1.0,
    return_visitor_ratio: float = 0.0,
    data_cache_ratio: float = 0.0,
) -> float:
    """SWDM v4 grams of CO2e per page view.

    ``grid_g_per_kwh`` applies to the operational segments only; embodied
    emissions keep the global intensity, as the model recommends. The green
    hosting factor reduces only the operational data-centre term. Return
    visitors load only the non-cached share of the data.
    """
    for name, value in (
        ("green_hosting_factor", green_hosting_factor),
        ("new_visitor_ratio", new_visitor_ratio),
        ("return_visitor_ratio", return_visitor_ratio),
        ("data_cache_ratio", data_cache_ratio),
    ):
        if not 0 <= value <= 1:
            raise ValueError(f"{name} must be between 0 and 1")
    if transferred_bytes < 0:
        raise ValueError("bytes must not be negative")
    gb = transferred_bytes / BYTES_PER_GB
    operational = {
        segment: gb * kwh * grid_g_per_kwh
        for segment, kwh in OPERATIONAL_KWH_PER_GB.items()
    }
    embodied = {
        segment: gb * kwh * GLOBAL_GRID_G_PER_KWH
        for segment, kwh in EMBODIED_KWH_PER_GB.items()
    }
    operational["data_center"] *= 1 - green_hosting_factor
    first_visit = sum(operational.values()) + sum(embodied.values())
    return first_visit * (
        new_visitor_ratio + return_visitor_ratio * (1 - data_cache_ratio)
    )


def visita(transferred_bytes: int) -> Visita:
    """One first visit with no green hosting: the conservative default."""
    total = emisiones_g(transferred_bytes)
    return Visita(
        bytes=transferred_bytes,
        kwh=energia_kwh(transferred_bytes),
        g_co2e=total,
        g_co2e_peru=emisiones_g(transferred_bytes, PERU_EMBER_G_PER_KWH),
        rating=rating(total),
    )


def proyeccion_anual(v: Visita, visitas: int) -> dict[str, float]:
    if visitas < 0:
        raise ValueError("visits must not be negative")
    return {
        "visitas": visitas,
        "kwh": v.kwh * visitas,
        "kg_co2e": v.g_co2e * visitas / 1000,
        "kg_co2e_peru": v.g_co2e_peru * visitas / 1000,
    }


def reduccion_pct(antes: float, despues: float) -> float:
    if antes <= 0:
        raise ValueError("ANTES must be positive")
    return (antes - despues) / antes * 100


def bytes_por_pagina(resultados: dict) -> dict[str, int]:
    """Median transferred bytes per page from an ECL-108/ECL-115 campaign.

    Pages without valid rounds (``NM`` in the evidence) are left out instead
    of being counted as zero.
    """
    pages = {}
    for page in resultados["pages"]:
        rounds = [r["transferredBytes"] for r in page.get("rounds", [])]
        if rounds:
            pages[page["path"]] = int(median(rounds))
    return pages


def calcular(
    antes: dict[str, int], despues: dict[str, int] | None, visitas: int
) -> dict:
    report: dict = {
        "modelo": "Sustainable Web Design Model v4",
        "kwh_por_gb": KWH_PER_GB,
        "intensidad_global_g_kwh": GLOBAL_GRID_G_PER_KWH,
        "intensidad_peru_g_kwh": PERU_EMBER_G_PER_KWH,
        "visitas_anuales": visitas,
        "paginas": {},
    }
    for path, size in antes.items():
        row: dict = {"antes": asdict(visita(size))}
        row["antes"]["anual"] = proyeccion_anual(visita(size), visitas)
        if despues and path in despues:
            after = visita(despues[path])
            row["despues"] = asdict(after) | {"anual": proyeccion_anual(after, visitas)}
            row["reduccion_pct"] = reduccion_pct(size, despues[path])
        report["paginas"][path] = row
    return report


def _formato(report: dict) -> str:
    lines = [
        f"SWDM v4: {report['kwh_por_gb']:.3f} kWh/GB; "
        f"{report['intensidad_global_g_kwh']:.0f} g/kWh global, "
        f"{report['intensidad_peru_g_kwh']:.2f} g/kWh Perú (operacional).",
        f"Proyección: {report['visitas_anuales']} visitas al año (supuesto).",
        "",
        "Página | Campaña | Bytes | MB | kWh/visita | g CO2e/visita | "
        "g CO2e Perú | Rating | kWh/año | kg CO2e/año",
    ]
    for path, row in report["paginas"].items():
        for campaign in ("antes", "despues"):
            if campaign not in row:
                continue
            v = row[campaign]
            lines.append(
                f"{path} | {campaign.upper()} | {v['bytes']} | "
                f"{v['bytes'] / 1e6:.2f} | {v['kwh']:.6f} | {v['g_co2e']:.4f} | "
                f"{v['g_co2e_peru']:.4f} | {v['rating']} | "
                f"{v['anual']['kwh']:.3f} | {v['anual']['kg_co2e']:.3f}"
            )
        if "reduccion_pct" in row:
            lines.append(f"{path} | reducción | {row['reduccion_pct']:.1f} %")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--antes", type=Path, default=ANTES_RESULTADOS)
    parser.add_argument("--despues", type=Path)
    parser.add_argument("--bytes", type=int, help="calcular un tamaño suelto")
    parser.add_argument(
        "--visitas-anuales", type=int, default=VISITAS_ANUALES_SUPUESTAS
    )
    parser.add_argument("--json", action="store_true", help="salida JSON")
    args = parser.parse_args(argv)

    if args.bytes is not None:
        antes = {"--bytes": args.bytes}
        despues = None
    else:
        antes = bytes_por_pagina(json.loads(args.antes.read_text("utf-8")))
        despues = (
            bytes_por_pagina(json.loads(args.despues.read_text("utf-8")))
            if args.despues
            else None
        )
    report = calcular(antes, despues, args.visitas_anuales)
    print(json.dumps(report, indent=2) if args.json else _formato(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
