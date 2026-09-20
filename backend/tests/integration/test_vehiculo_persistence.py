from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.models import Vehiculo

pytestmark = pytest.mark.integration


def vehicle_values(**overrides):
    values = {
        "placa": "X-1",
        "tipo": "CAMIONETA",
        "capacidad_kg": Decimal("1250.50"),
        "capacidad_m3": Decimal("8.75"),
        "rendimiento_km_l": Decimal("11.250"),
        "factor_co2_kg_km": Decimal("0.31415"),
        "anio_fabricacion": 2024,
    }
    values.update(overrides)
    return values


def test_vehicle_valid_persistence_defaults_and_exact_decimals(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    with Session(engine) as session:
        vehicle = Vehiculo(**vehicle_values())
        session.add(vehicle)
        session.commit()
        session.refresh(vehicle)

        assert vehicle.vehiculo_id is not None
        assert vehicle.estado == "ACTIVO"
        assert vehicle.placa == "X-1"
        assert vehicle.capacidad_kg == Decimal("1250.50")
        assert vehicle.capacidad_m3 == Decimal("8.75")
        assert vehicle.rendimiento_km_l == Decimal("11.250")
        assert vehicle.factor_co2_kg_km == Decimal("0.31415")

        zero_emission = Vehiculo(
            **vehicle_values(placa="EV-0", factor_co2_kg_km=Decimal("0"))
        )
        session.add(zero_emission)
        session.commit()
        assert zero_emission.factor_co2_kg_km == Decimal("0.00000")


@pytest.mark.parametrize("placa", ["ABC123", "ABC-123", "ABC 123"])
def test_vehicle_plate_accepts_canonical_values_and_internal_space(
    migration_database, placa
):
    engine, config = migration_database
    command.upgrade(config, "head")
    with Session(engine) as session:
        vehicle = Vehiculo(**vehicle_values(placa=placa))
        session.add(vehicle)
        session.commit()
        assert vehicle.placa == placa


@pytest.mark.parametrize(
    "overrides",
    [
        {"placa": ""},
        {"placa": "   "},
        {"placa": "\tABC123"},
        {"placa": "ABC123\t"},
        {"placa": "\nABC123"},
        {"placa": "ABC123\n"},
        {"placa": " ABC123 "},
        {"placa": "abc123"},
        {"placa": "X-2", "tipo": "INVALIDO"},
        {"placa": "X-3", "capacidad_kg": Decimal("0")},
        {"placa": "X-4", "capacidad_kg": Decimal("-1")},
        {"placa": "X-5", "capacidad_m3": Decimal("0")},
        {"placa": "X-6", "capacidad_m3": Decimal("-1")},
        {"placa": "X-7", "rendimiento_km_l": Decimal("0")},
        {"placa": "X-8", "rendimiento_km_l": Decimal("-1")},
        {"placa": "X-9", "factor_co2_kg_km": Decimal("-0.00001")},
        {"placa": "X-10", "anio_fabricacion": 1979},
        {"placa": "X-11", "anio_fabricacion": 2101},
    ],
)
def test_vehicle_constraints_reject_invalid_values_and_session_recovers(
    migration_database, overrides
):
    engine, config = migration_database
    command.upgrade(config, "head")
    with Session(engine) as session:
        session.add(Vehiculo(**vehicle_values(**overrides)))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        valid = Vehiculo(**vehicle_values(placa="RECOVERED"))
        session.add(valid)
        session.commit()
        assert valid.vehiculo_id is not None


def test_vehicle_duplicate_plate_is_rejected_and_session_recovers(
    migration_database,
):
    engine, config = migration_database
    command.upgrade(config, "head")
    with Session(engine) as session:
        session.add(Vehiculo(**vehicle_values()))
        session.commit()
        session.add(Vehiculo(**vehicle_values()))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        valid = Vehiculo(**vehicle_values(placa="UNIQUE-2"))
        session.add(valid)
        session.commit()
        assert valid.vehiculo_id is not None


def test_vehicle_database_assigns_active_server_default(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    with engine.begin() as connection:
        identifier = connection.scalar(
            text(
                """
                INSERT INTO vehiculo (
                    placa, tipo, capacidad_kg, capacidad_m3,
                    rendimiento_km_l, factor_co2_kg_km, anio_fabricacion
                ) VALUES (
                    :placa, :tipo, :capacidad_kg, :capacidad_m3,
                    :rendimiento_km_l, :factor_co2_kg_km, :anio_fabricacion
                )
                RETURNING vehiculo_id
                """
            ),
            vehicle_values(placa="SQL-1"),
        )
        assert (
            connection.scalar(
                text("SELECT estado FROM vehiculo WHERE vehiculo_id = :identifier"),
                {"identifier": identifier},
            )
            == "ACTIVO"
        )
