"""Protecciones de scripts/seed_demo.py: nunca toca una base que no sea demo."""

from unittest.mock import patch

import pytest

from app.core.rbac import Rol
from scripts.seed_demo import (
    DRIVERS,
    PASSWORD_PREFIX,
    USERS,
    SeedRefused,
    ensure_demo_target,
    main,
    read_passwords,
)

DEMO_URL = "postgresql+psycopg://user@127.0.0.1:5432/ecologistica_demo"
PASSWORDS = {PASSWORD_PREFIX + role.value: "x" * 16 for role in Rol}


def test_ruta_dorada_base_demo_y_contrasenas_validas():
    ensure_demo_target(DEMO_URL, "development")
    assert set(read_passwords(PASSWORDS)) == set(Rol)


@pytest.mark.parametrize(
    "url,env",
    [
        ("postgresql+psycopg://user@127.0.0.1:5432/ecologistica", "development"),
        ("postgresql+psycopg://user@127.0.0.1:5432/ecologistica_test", "test"),
        ("postgresql+psycopg://user@127.0.0.1:5432/demo_produccion", None),
        (DEMO_URL, "production"),
        (DEMO_URL, " Production "),
        (None, "development"),
        ("no es una url", "development"),
    ],
)
def test_ruta_infeliz_rechaza_bases_no_demo_o_produccion(url, env):
    with pytest.raises(SeedRefused):
        ensure_demo_target(url, env)


@pytest.mark.parametrize("length", [0, 11])
def test_ruta_de_borde_contrasena_corta_o_ausente(length):
    environ = dict(PASSWORDS)
    environ[PASSWORD_PREFIX + "AUDITOR"] = "x" * length
    with pytest.raises(SeedRefused, match="SEED_DEMO_PASSWORD_AUDITOR"):
        read_passwords(environ)


def test_ruta_de_borde_doce_caracteres_es_el_minimo():
    environ = dict(PASSWORDS)
    environ[PASSWORD_PREFIX + "AUDITOR"] = "x" * 12
    assert read_passwords(environ)[Rol.AUDITOR] == "x" * 12


def test_ruta_infeliz_main_no_abre_conexion_si_rechaza(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", DEMO_URL.replace("_demo", "_dev"))
    with patch("scripts.seed_demo.build_engine") as build_engine:
        assert main(PASSWORDS) == 2
    build_engine.assert_not_called()
    assert "_demo" in capsys.readouterr().err


def test_ruta_feliz_main_siembra_e_informa_sin_contrasenas(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", DEMO_URL)
    with (
        patch("scripts.seed_demo.build_engine") as build_engine,
        patch("scripts.seed_demo.seed") as seed,
    ):
        seed.return_value.created = {"pedidos": 20}
        seed.return_value.existing = {}
        assert main({**PASSWORDS, "APP_ENV": "development"}) == 0
    build_engine.return_value.dispose.assert_called_once()
    output = capsys.readouterr().out
    assert "pedidos: 20 creados" in output
    assert "x" * 16 not in output


def test_datos_claramente_ficticios():
    assert all(email.endswith("@ecologistica.example") for email in USERS.values())
    assert all(driver.email.endswith("@ecologistica.example") for driver in DRIVERS)
    assert all(driver.dni.startswith("9000000") for driver in DRIVERS)
    assert sum(driver.licencia_vencida for driver in DRIVERS) == 1
    assert sum(driver.sin_disponibilidad for driver in DRIVERS) == 1
