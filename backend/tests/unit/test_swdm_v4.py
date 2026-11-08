"""ECL-116: SWDM v4 calculation, cross-checked against CO2.js 0.19.0.

The expected values come from running ``@tgwf/co2`` 0.19.0
(``new co2({model: "swd", version: 4})``) on the same inputs.
"""

import json

import pytest

from scripts import swdm_v4 as swdm


def test_coefficients_are_swdm_v4_not_v3():
    assert swdm.KWH_PER_GB == pytest.approx(0.300)
    assert swdm.GLOBAL_GRID_G_PER_KWH == 494
    assert swdm.BYTES_PER_GB == 10**9


@pytest.mark.parametrize(
    "size,expected",
    [
        (10**9, 148.2),
        (11_434_626, 1.6946115732),
        (11_438_644, 1.6952070408),
        (1_183, 0.0001753206),
    ],
)
def test_per_visit_matches_co2js(size, expected):
    assert swdm.emisiones_g(size) == pytest.approx(expected, rel=1e-9)


def test_regional_grid_applies_to_operational_segments_only():
    """CO2.js perByteTrace with gridIntensity 263.27 on every segment."""
    assert swdm.emisiones_g(11_434_626, swdm.PERU_EMBER_G_PER_KWH) == pytest.approx(
        1.18277918934588, rel=1e-9
    )


def test_green_hosting_removes_operational_data_centre_only():
    """CO2.js perByte(bytes, green=true)."""
    assert swdm.emisiones_g(11_434_626, green_hosting_factor=1) == pytest.approx(
        1.38393278478, rel=1e-9
    )


def test_return_visitors_load_only_the_non_cached_share():
    """CO2.js perVisit with 75 % first, 25 % return and 2 % reloaded."""
    assert swdm.emisiones_g(
        11_434_626,
        new_visitor_ratio=0.75,
        return_visitor_ratio=0.25,
        data_cache_ratio=0.98,
    ) == pytest.approx(1.279431737766, rel=1e-9)


@pytest.mark.parametrize(
    "grams,grade",
    [
        (0.0, "A+"),
        (0.040, "A+"),
        (0.0401, "A"),
        (0.079, "A"),
        (0.145, "B"),
        (0.209, "C"),
        (0.278, "D"),
        (0.359, "E"),
        (0.3591, "F"),
        (1.69, "F"),
    ],
)
def test_rating_bands_are_inclusive_upper_bounds(grams, grade):
    assert swdm.rating(grams) == grade


@pytest.mark.parametrize(
    "keyword",
    ["green_hosting_factor", "new_visitor_ratio", "return_visitor_ratio"],
)
@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_ratios_outside_zero_one_are_rejected(keyword, value):
    with pytest.raises(ValueError, match=keyword):
        swdm.emisiones_g(1000, **{keyword: value})


def test_negative_inputs_are_rejected():
    with pytest.raises(ValueError):
        swdm.emisiones_g(-1)
    with pytest.raises(ValueError):
        swdm.proyeccion_anual(swdm.visita(1000), -1)
    with pytest.raises(ValueError):
        swdm.reduccion_pct(0, 10)


def test_visit_and_annual_projection():
    visit = swdm.visita(11_434_626)
    assert visit.kwh == pytest.approx(0.0034303878)
    assert visit.rating == "F"
    annual = swdm.proyeccion_anual(visit, 4_500)
    assert annual["kwh"] == pytest.approx(15.43674510)
    assert annual["kg_co2e"] == pytest.approx(7.62575208, rel=1e-8)
    assert swdm.VISITAS_ANUALES_SUPUESTAS == 15 * 1 * 300


def test_rubric_weight_target_gets_a_c_rating():
    """1.1 MB, the Inspección 4 weight target, as a reference point."""
    assert swdm.visita(1_100_000).rating == "C"


def test_pages_without_valid_rounds_are_not_counted_as_zero():
    resultados = {
        "pages": [
            {"path": "/login", "rounds": [{"transferredBytes": b} for b in (5, 1, 3)]},
            {"path": "/vehiculos", "rounds": []},
        ]
    }
    assert swdm.bytes_por_pagina(resultados) == {"/login": 3}


def test_baseline_evidence_is_read_from_ecl108():
    pages = swdm.bytes_por_pagina(json.loads(swdm.ANTES_RESULTADOS.read_text("utf-8")))
    assert pages == {"/login": 11_434_626, "/conductor/itinerario": 11_438_644}


def test_after_evidence_is_the_first_load_campaign_of_ecl115():
    antes = swdm.bytes_por_pagina(json.loads(swdm.ANTES_RESULTADOS.read_text("utf-8")))
    despues = swdm.bytes_por_pagina(
        json.loads(swdm.DESPUES_RESULTADOS.read_text("utf-8"))
    )
    assert despues == {"/login": 433_643, "/conductor/itinerario": 459_748}
    report = swdm.calcular(antes, despues, swdm.VISITAS_ANUALES_SUPUESTAS)
    login = report["paginas"]["/login"]
    itinerario = report["paginas"]["/conductor/itinerario"]
    assert login["reduccion_pct"] == pytest.approx(96.2076, abs=1e-3)
    assert itinerario["reduccion_pct"] == pytest.approx(95.9807, abs=1e-3)
    assert login["despues"]["rating"] == itinerario["despues"]["rating"] == "A"


def test_service_worker_reload_is_a_repeat_visit_not_a_first_load():
    recarga = swdm.bytes_por_pagina(
        json.loads(swdm.DESPUES_RECARGA_SW.read_text("utf-8"))
    )
    assert recarga == {"/login": 1_020, "/conductor/itinerario": 3_103}


def test_cli_uses_the_ecl115_first_load_by_default(capsys):
    assert swdm.main(["--despues"]) == 0
    salida = capsys.readouterr().out
    assert "/login | DESPUES | 433643" in salida
    assert "/login | reducción | 96.2 %" in salida


def test_report_compares_antes_and_despues():
    report = swdm.calcular({"/login": 2_000_000}, {"/login": 500_000}, 100)
    row = report["paginas"]["/login"]
    assert row["reduccion_pct"] == pytest.approx(75.0)
    assert row["despues"]["g_co2e"] == pytest.approx(row["antes"]["g_co2e"] / 4)
    assert row["despues"]["anual"]["visitas"] == 100


def test_cli_text_and_json(tmp_path, capsys):
    despues = tmp_path / "despues.json"
    despues.write_text(
        json.dumps(
            {"pages": [{"path": "/login", "rounds": [{"transferredBytes": 900_000}]}]}
        ),
        "utf-8",
    )
    assert swdm.main(["--despues", str(despues)]) == 0
    text = capsys.readouterr().out
    assert "/login | DESPUES | 900000" in text
    assert "reducción" in text
    assert swdm.main(["--bytes", "1100000", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["paginas"]["--bytes"]["antes"]["rating"] == "C"
