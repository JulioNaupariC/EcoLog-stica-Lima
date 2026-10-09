from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.schemas.conductor import ConductorCreate, ConductorData, ConductorUpdate


def payload(**changes):
    start = datetime.now(timezone.utc) + timedelta(days=1)
    data = {
        "nombre": " Rosa Prueba ",
        "dni": "01234567",
        "licencia_numero": " lic-01 ",
        "licencia_vigente_hasta": "2099-12-31",
        "experiencia_anios": 2,
        "telefono": "+51987654321",
        "punto_partida": " Base Lima ",
        "disponible_desde": start.isoformat(),
        "disponible_hasta": (start + timedelta(hours=9)).isoformat(),
        "email": "driver@example.test",
        "password": "test-only-initial-password",
    }
    data.update(changes)
    return data


def test_normalization_and_secret_representation():
    row = ConductorCreate.model_validate(payload())
    assert row.nombre == "Rosa Prueba"
    assert row.licencia_numero == "LIC-01"
    assert row.punto_partida == "Base Lima"
    assert row.dni == "01234567"
    assert row.disponible_desde.tzinfo == timezone.utc
    assert row.password.get_secret_value() not in repr(row)


@pytest.mark.parametrize(
    "changes",
    [
        {"dni": "123"},
        {"dni": "abcdefgh"},
        {"dni": "１２３４５６７８"},
        {"nombre": " "},
        {"licencia_numero": " "},
        {"licencia_numero": "X" * 21},
        {"telefono": "987654321"},
        {"telefono": "+012345678"},
        {"punto_partida": " "},
        {"experiencia_anios": -1},
        {"experiencia_anios": True},
        {"experiencia_anios": 1.2},
        {"experiencia_anios": 2147483648},
        {"licencia_vigente_hasta": "invalid"},
        {"disponible_desde": "2099-01-01T08:00:00"},
        {"disponible_desde": None},
        {"disponible_hasta": None},
        {"disponible_desde": None, "disponible_hasta": None},
        {"disponible_hasta": "2000-01-01T08:00:00Z"},
        {"email": "invalid"},
        {"password": ""},
        {"password_hash": "client-hash"},
        {"usuario_id": "client-owner"},
        {"rol": "ADMINISTRADOR"},
        {"estado": "ACTIVO"},
    ],
)
def test_invalid_registration(changes):
    with pytest.raises(ValidationError):
        ConductorCreate.model_validate(payload(**changes))


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"nombre": None},
        {"dni": None},
        {"email": "cannot-change@example.test"},
        {"password": "cannot-change"},
        {"usuario_id": "cannot-change"},
        {"disponible_desde": None},
        {"disponible_hasta": None},
    ],
)
def test_invalid_patch(changes):
    with pytest.raises(ValidationError):
        ConductorUpdate.model_validate(changes)


def test_clear_availability_and_expired_license_are_valid_profile_data():
    patch = ConductorUpdate(disponible_desde=None, disponible_hasta=None)
    assert patch.model_fields_set == {"disponible_desde", "disponible_hasta"}
    data = payload(licencia_vigente_hasta="2000-01-01")
    data.pop("email")
    data.pop("password")
    assert ConductorData.model_validate(data).licencia_vigente_hasta.year == 2000
    with pytest.raises(ValidationError):
        ConductorData.model_validate(
            {**data, "disponible_hasta": data["disponible_desde"]}
        )
