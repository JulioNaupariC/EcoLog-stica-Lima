from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.vehiculo import VehicleCreate, VehicleUpdate


def valid_vehicle(**changes):
    data = {
        "placa": "ABC123",
        "tipo": "CAMIONETA",
        "capacidad_kg": Decimal("1000.00"),
        "capacidad_m3": Decimal("8.00"),
        "rendimiento_km_l": Decimal("10.000"),
        "factor_co2_kg_km": Decimal("0.30000"),
        "anio_fabricacion": 2024,
    }
    data.update(changes)
    return data


@pytest.mark.parametrize(
    "raw,expected",
    [
        (" abc-123\t", "ABC-123"),
        ("\u2003abc123\u2003", "ABC123"),
        ("abc 123", "ABC 123"),
    ],
)
def test_plate_normalization_preserves_internal_content(raw, expected):
    assert VehicleCreate(**valid_vehicle(placa=raw)).placa == expected


@pytest.mark.parametrize(
    "changes",
    [
        {"placa": "   "},
        {"placa": "ABCDEFGHIJK"},
        {"tipo": "AUTO"},
        {"anio_fabricacion": 1979},
        {"anio_fabricacion": 2101},
        {"capacidad_kg": Decimal("NaN")},
        {"capacidad_m3": Decimal("Infinity")},
        {"rendimiento_km_l": Decimal("-Infinity")},
        {"factor_co2_kg_km": Decimal("-0.00001")},
        {"capacidad_kg": Decimal("100000000.00")},
        {"capacidad_m3": Decimal("1.001")},
        {"rendimiento_km_l": Decimal("1.0001")},
        {"factor_co2_kg_km": Decimal("1.000001")},
        {"unexpected": "secret"},
    ],
)
def test_create_rejects_invalid_fields(changes):
    with pytest.raises(ValidationError):
        VehicleCreate(**valid_vehicle(**changes))


def test_zero_emission_factor_is_valid():
    assert VehicleCreate(
        **valid_vehicle(factor_co2_kg_km=Decimal("0"))
    ).factor_co2_kg_km == Decimal("0")


@pytest.mark.parametrize("payload", [{}, {"placa": None}, {"estado": "INACTIVO"}])
def test_patch_rejects_empty_null_and_forbidden_fields(payload):
    with pytest.raises(ValidationError):
        VehicleUpdate.model_validate(payload)


def test_patch_normalizes_plate_and_tracks_only_supplied_fields():
    update = VehicleUpdate(placa=" abc-123 ")
    assert update.model_dump(exclude_unset=True) == {"placa": "ABC-123"}
