"""ECL-105: escenario de la demo del MVP sin base de datos."""

from datetime import date
from unittest.mock import patch

import pytest

from app.core.rbac import Rol
from app.optimizacion import sinteticos
from app.schemas.conductor import ConductorCreate
from scripts import seed_demo
from scripts.seed_demo_mvp import (
    PREFIJO_PEDIDO,
    TOTAL_PEDIDOS,
    VEHICULOS,
    SeedMvpRefused,
    conductores_demo,
    distrito_de,
    main,
    parse_fecha,
    pedidos_demo,
)

DEMO_URL = "postgresql+psycopg://user@127.0.0.1:5432/ecologistica_demo"
PASSWORDS = {seed_demo.PASSWORD_PREFIX + role.value: "x" * 16 for role in Rol}


def test_ruta_dorada_150_pedidos_en_los_cuatro_distritos():
    pedidos = pedidos_demo()
    assert len(pedidos) == TOTAL_PEDIDOS
    assert len({p.referencia for p in pedidos}) == TOTAL_PEDIDOS
    assert all(p.referencia.startswith(PREFIJO_PEDIDO) for p in pedidos)
    assert {p.distrito for p in pedidos} == set(sinteticos.DISTRITOS)
    # Two infeasible orders on purpose, to show "no asignado con motivo".
    assert {p.vrp.pedido_id for p in pedidos} >= {"X-CAPACIDAD", "X-VENTANA"}


def test_ruta_feliz_el_escenario_es_el_mismo_en_cada_pc():
    assert pedidos_demo() == pedidos_demo()


def test_ruta_dorada_15_vehiculos_en_total():
    assert len(VEHICULOS) + len(seed_demo.VEHICLES) == 15
    assert len({placa for placa, _ in VEHICULOS}) == len(VEHICULOS)
    assert {tipo for _, tipo in VEHICULOS} <= set(sinteticos.FLOTA)


def test_ruta_dorada_conductores_nuevos_validos_y_sin_choques():
    nuevos = conductores_demo()
    assert len(nuevos) == 13
    previos = seed_demo.DRIVERS
    for campo in ("dni", "email", "licencia", "telefono"):
        valores = [getattr(d, campo) for d in (*previos, *nuevos)]
        assert len(set(valores)) == len(valores), campo
    for driver in nuevos:
        ConductorCreate.model_validate(
            {
                "nombre": driver.nombre,
                "dni": driver.dni,
                "licencia_numero": driver.licencia,
                "licencia_vigente_hasta": "2029-12-31",
                "experiencia_anios": 3,
                "telefono": driver.telefono,
                "punto_partida": "Base",
                "disponible_desde": "2026-11-20T08:00:00-05:00",
                "disponible_hasta": "2026-11-20T18:00:00-05:00",
                "email": driver.email,
                "password": "test-only-password",
            }
        )


def test_ruta_de_borde_distrito_fuera_de_las_cajas():
    assert distrito_de(-12.0470, -76.9680) == "Santa Anita"
    with pytest.raises(ValueError):
        distrito_de(-12.12, -77.03)  # Miraflores


@pytest.mark.parametrize(
    ("texto", "error"),
    [("20-11-2026", "formato"), ("2026-11-10", "pasado")],
)
def test_ruta_infeliz_fecha_invalida_o_pasada(texto, error):
    with pytest.raises(SeedMvpRefused, match=error):
        parse_fecha(texto, date(2026, 11, 11))


def test_ruta_de_borde_hoy_es_valido():
    assert parse_fecha("2026-11-11", date(2026, 11, 11)) == date(2026, 11, 11)


def test_ruta_infeliz_main_no_abre_conexion_fuera_de_demo(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", DEMO_URL.replace("_demo", "_dev"))
    with patch("scripts.seed_demo_mvp.build_engine") as build_engine:
        assert main(["--fecha", "2099-01-01"], PASSWORDS) == 2
    build_engine.assert_not_called()
    assert "_demo" in capsys.readouterr().err


def test_ruta_infeliz_main_informa_fecha_ocupada(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", DEMO_URL)
    with (
        patch("scripts.seed_demo_mvp.build_engine") as build_engine,
        patch("scripts.seed_demo_mvp.seed_mvp", side_effect=SeedMvpRefused("ocupada")),
    ):
        assert main(["--fecha", "2099-01-01"], {**PASSWORDS, "APP_ENV": "dev"}) == 2
    build_engine.return_value.dispose.assert_called_once()
    assert "ocupada" in capsys.readouterr().err


def test_ruta_feliz_main_resume_sin_contrasenas(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", DEMO_URL)
    with (
        patch("scripts.seed_demo_mvp.build_engine") as build_engine,
        patch("scripts.seed_demo_mvp.seed_mvp") as seed_mvp,
        patch("scripts.seed_demo_mvp.resumen_fecha") as resumen,
    ):
        seed_mvp.return_value.created = {"pedidos": 150}
        seed_mvp.return_value.existing = {}
        resumen.return_value = {"pedidos_pendientes": 150, "vehiculos_activos": 15}
        assert main(["--fecha", "2099-01-01"], {**PASSWORDS, "APP_ENV": "dev"}) == 0
    build_engine.return_value.dispose.assert_called_once()
    output = capsys.readouterr().out
    assert "150 pedidos PENDIENTE y 15 vehículos ACTIVO" in output
    assert "x" * 16 not in output
