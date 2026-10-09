"""Render a standalone report strictly from recorded campaign results."""

# ruff: noqa: E501
# HTML/CSS strings keep readable markup rather than Python line wrapping.

import argparse
import html
import json
from pathlib import Path


def number(value: float | None, digits: int = 3) -> str:
    return "Sin datos" if value is None else f"{value:,.{digits}f}"


def badge(passed: bool) -> str:
    return (
        '<span class="pass">CUMPLE</span>'
        if passed
        else '<span class="fail">NO ACREDITADO</span>'
    )


def render(directory: Path) -> Path:
    consolidated = directory / "campaign-consolidated.json"
    campaign = json.loads(
        (
            consolidated if consolidated.exists() else directory / "campaign.json"
        ).read_text(encoding="utf-8")
    )
    environment = json.loads(
        (directory / "environment.json").read_text(encoding="utf-8")
    )
    rows = campaign["results"]
    stress_description = (
        f"{campaign['completed_stress_windows']} mediciones terminadas (10 min programados) y una corrida interrumpida conservada"
        if campaign.get("recovery_included")
        else f"{sum(row['profile'] == 'stress' for row in rows)} perfiles de estrés exportados"
    )
    cards = []
    table = []
    availability = []
    slot_notes = []
    audit_path = directory / "audit.json"
    audited = (
        json.loads(audit_path.read_text()).get("availability_slots", {})
        if audit_path.exists()
        else {}
    )
    for row in rows:
        label = row.get("report_label", row["run"])
        concurrency = row["concurrency"]
        table.append(f"""<tr><th>{html.escape(label)}</th>
<td>{row["attempts"]:,}<br><small>HTTP {html.escape(str(row["http_statuses"]))}</small></td><td>{row["unique_valid_persisted"]:,}</td>
<td>{number(row["p95_valid_seconds"])} s<br>{badge(row["p95_threshold_pass"])}</td>
<td>{number(row["http_5xx_percent"])}% ({row["http_5xx"]}/{row["http_responses"]})<br>{badge(row["http_5xx_threshold_pass"])}</td>
<td>{row["functional_or_transport_errors"]}</td><td>{row["without_response"]}</td><td>{row["persistence_discrepancies"]}</td></tr>""")
        observed = row["availability"]
        slots = audited.get(row["run"])
        if slots:
            slot_notes.append(
                f"<li><strong>{html.escape(label)}</strong>: "
                f"{slots['available_slots']}/{slots['expected_slots']} intervalos de muestreo correctos; "
                f"{slots['unavailable_slots']} fallidos, {slots['missing_slots']} sin datos, "
                f"{slots['duplicate_samples']} muestras repetidas en un intervalo. "
                f"Proporción conservadora de intervalos: {number(slots['conservative_available_percent'], 2)}%.</li>"
            )
        availability.append(f"""<tr><th>{html.escape(label)}</th>
<td>{observed["samples"]}</td><td>{observed["available"]}</td><td>{observed["unavailable"]}</td>
<td>{observed["estimated_missing_slots"]}</td><td>{number(observed["successful_samples_percent"], 2)}%</td>
<td>{html.escape(str(observed["first_utc"]))}<br>{html.escape(str(observed["last_utc"]))}</td></tr>""")
        if row["profile"] == "stress":
            monitors = [
                json.loads(line)
                for line in (
                    directory
                    / row.get("evidence_directory", row["run"])
                    / "monitor.jsonl"
                )
                .read_text()
                .splitlines()
            ]
            samples = [
                item
                for item in monitors
                if 0 <= item.get("stable_offset", -1) < concurrency["expected_seconds"]
                and item.get("inflight") is not None
            ]
            points = " ".join(
                f"{40 + item['stable_offset'] * 880 / concurrency['expected_seconds']:.1f},{180 - min(item['inflight'], 150):.1f}"
                for item in samples
            )
            cards.append(f'''<article><h3>{html.escape(label)} · concurrencia observada</h3>
<p>Mínimo {concurrency["minimum"]}; máximo {concurrency["maximum"]}; ≥100 en {concurrency["seconds_at_least_100"]}/{concurrency["expected_seconds"]} segundos ({number(concurrency["percent_seconds_at_least_100"], 2)}%).
Faltan {concurrency["missing_seconds"]} segundos. {badge(concurrency["sustained_100_pass"])}</p>
<svg viewBox="0 0 960 220" role="img" aria-label="Serie de solicitudes en vuelo del servidor">
<line x1="40" y1="80" x2="920" y2="80" stroke="#be123c" stroke-dasharray="6 5"/>
<text x="40" y="65">Umbral: 100 solicitudes en vuelo</text>
<polyline points="{points}" fill="none" stroke="#0369a1" stroke-width="2"/>
<text x="40" y="210">Inicio de fase estable</text><text x="750" y="210">{concurrency["expected_seconds"]} segundos</text></svg>
<p>Retraso máximo del muestreador: {number(row["generator"]["max_scheduler_lag_seconds"])} s.
CPU máxima del generador: {number(row["generator"]["max_cpu_percent_one_core_basis"], 1)}% de un núcleo.</p></article>''')
    content = f"""<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>ECL-61 · ST-035 · Resultados medidos</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;background:#edf3f6;color:#172b3a;margin:0}}
main{{max-width:1240px;margin:auto;padding:36px}}h1{{font-size:32px;margin:0}}h2{{margin-top:36px}}
header,article,.panel{{background:white;padding:24px;border-radius:12px;margin-bottom:20px}}
.subtitle{{color:#475569}}.notice{{border-left:5px solid #b45309;background:#fff7ed;padding:16px}}
table{{border-collapse:collapse;width:100%;font-size:14px;background:white}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #cbd5e1}}
thead{{background:#123b4a;color:white}}.pass{{color:#166534;font-weight:700}}.fail{{color:#b91c1c;font-weight:700}}
svg{{width:100%;background:#f8fafc}}svg text{{font:13px system-ui;fill:#475569}}code{{word-break:break-all}}
a{{color:#0369a1}}
</style><main><header><p class="subtitle">EcoLogística Lima · ECL-61 / ST-035 · RNF-007 y RNF-008</p>
<h1>Pruebas de carga y disponibilidad</h1><p>Resultados reales · {html.escape(environment["started_utc"])}</p>
<p>1,000 pedidos de jornada sintética · 50 vehículos por base · {environment["parameters"]["users"]} clientes de estrés · {stress_description}</p></header>
<p class="notice"><strong>Alcance de la evidencia:</strong> jornada comprimida a {environment["parameters"]["daily_seconds"]} segundos.
Las mediciones verifican los umbrales; no acreditan RNF-008 si faltan 100 solicitudes activas sostenidas.
La consulta del tablero depende de ECL-15. No se ha medido el SLA mensual.</p>
<h2>Registro de pedidos: latencia y errores</h2><table><thead><tr><th>Perfil</th><th>Intentos / HTTP</th><th>Válidos persistidos</th><th>P95 ≤2 s</th><th>5xx &lt;1%</th><th>Errores func./red</th><th>Sin respuesta</th><th>Diferencias BD</th></tr></thead><tbody>{"".join(table)}</tbody></table>
<p>P95 agregado de estrés: <strong>{number(campaign["aggregate_stress_p95_seconds"])} s</strong> sobre {campaign["aggregate_population"]:,} respuestas válidas conciliadas.
Rango más próximo; no se promedian percentiles. Agregado diagnóstico cuando alguna repetición no acredita la carga.</p>
<p>Perfiles del agregado: {html.escape(str(campaign.get("aggregate_selected_profiles", "perfiles de estrés exportados")))}.
La corrida interrumpida, cuando existe, permanece visible y se excluye del agregado consolidado.</p>
<h2>Disponibilidad durante la observación</h2><table><thead><tr><th>Perfil</th><th>Sondeos</th><th>Correctos</th><th>Fallidos</th><th>Huecos estimados</th><th>Éxito de muestras</th><th>Ventana UTC</th></tr></thead><tbody>{"".join(availability)}</tbody></table>
<p>GET /health y /health/ready (SELECT 1), cada segundo desde el mismo equipo. El porcentaje describe las muestras observadas; no garantiza continuidad entre sondeos. Los huecos no cuentan como disponibles. Los intervalos entre corridas quedan fuera de observación. <strong>SLA mensual: NO MEDIDO.</strong></p>
<h3>Control de huecos y sondeos duplicados</h3><ul>{"".join(slot_notes)}</ul>
<p>Reanálisis por intervalos de un segundo desde la primera hasta la última observación (asignación al intervalo más próximo). Una muestra de recuperación no rellena un intervalo perdido. Cualquier fallo dentro de un intervalo lo marca fallido. Es una estimación de cobertura del sondeo, sin garantía de disponibilidad continua ni SLA.</p>
<h2>Concurrencia del servidor</h2>{"".join(cards)}
<section class="panel"><h2>Entorno y trazabilidad</h2><p>{html.escape(environment["platform"])} · {environment["logical_cpus"]} CPU lógicas · {number(environment["ram_bytes"] / 1024**3, 1)} GiB RAM · 1 worker / 1 réplica.</p>
<p>API, generador y PostgreSQL locales sobre 127.0.0.1. Python {html.escape(environment["python"].split()[0])}; Locust {environment["packages"]["locust"]}.</p>
<p>Base Git: <code>{environment["git_base"]}</code>; cambios de ST-035 pendientes de commit durante la ejecución.</p>
<p>Fuentes: <a href="campaign.json">campaign.json</a>, <a href="environment.json">environment.json</a>, manifiestos, registros JSONL comprimidos, conciliación SQL, métricas Prometheus y logs por perfil.</p></section></main></html>"""
    target = directory / "reporte.html"
    target.write_text(content, encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(render(args.directory.resolve()))


if __name__ == "__main__":
    main()
