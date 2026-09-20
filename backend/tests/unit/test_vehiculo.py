import importlib.util
import re
from pathlib import Path

from sqlalchemy import CheckConstraint, Index, Numeric, SmallInteger, String

from app.models.vehiculo import TIPOS_VEHICULO, Vehiculo

EXPECTED_TYPES = ("CAMIONETA", "FURGON", "MOTO")
EXPECTED_PLATE_CHECK = (
    "length(placa) > 0 AND placa = upper(placa) "
    "AND left(placa, 1) !~ '[[:space:]]' "
    "AND right(placa, 1) !~ '[[:space:]]'"
)
EXPECTED_NUMERIC_CHECKS = {
    "ck_vehiculo_capacidad_kg": ("capacidad_kg <> 'NaN'::numeric AND capacidad_kg > 0"),
    "ck_vehiculo_capacidad_m3": ("capacidad_m3 <> 'NaN'::numeric AND capacidad_m3 > 0"),
    "ck_vehiculo_rendimiento_km_l": (
        "rendimiento_km_l <> 'NaN'::numeric AND rendimiento_km_l > 0"
    ),
    "ck_vehiculo_factor_co2_kg_km": (
        "factor_co2_kg_km <> 'NaN'::numeric AND factor_co2_kg_km >= 0"
    ),
}
EXPECTED_CONSTRAINTS = {
    "uq_vehiculo_placa",
    "ck_vehiculo_placa_canonica",
    "ck_vehiculo_tipo",
    "ck_vehiculo_capacidad_kg",
    "ck_vehiculo_capacidad_m3",
    "ck_vehiculo_rendimiento_km_l",
    "ck_vehiculo_factor_co2_kg_km",
    "ck_vehiculo_anio_fabricacion",
}


def _check_values(constraint: CheckConstraint) -> tuple[str, ...]:
    return tuple(re.findall(r"'([^']+)'", str(constraint.sqltext)))


def test_approved_vehicle_schema_and_safe_representation():
    table = Vehiculo.__table__
    assert table.name == "vehiculo"
    assert tuple(table.columns.keys()) == (
        "vehiculo_id",
        "placa",
        "tipo",
        "capacidad_kg",
        "capacidad_m3",
        "rendimiento_km_l",
        "factor_co2_kg_km",
        "anio_fabricacion",
        "estado",
    )
    assert all(not column.nullable for column in table.columns)
    assert table.c.vehiculo_id.primary_key
    assert str(table.c.vehiculo_id.server_default.arg) == "gen_random_uuid()"
    assert isinstance(table.c.placa.type, String) and table.c.placa.type.length == 10
    assert isinstance(table.c.tipo.type, String) and table.c.tipo.type.length == 20
    assert isinstance(table.c.estado.type, String) and table.c.estado.type.length == 15
    assert isinstance(table.c.anio_fabricacion.type, SmallInteger)
    assert str(table.c.estado.server_default.arg) == "'ACTIVO'"
    assert "creado_en" not in table.c and "actualizado_en" not in table.c
    assert repr(Vehiculo(placa="SECRET")) == "<Vehiculo>"


def test_vehicle_numeric_precision_constraints_and_index():
    table = Vehiculo.__table__
    expected_numeric = {
        "capacidad_kg": (10, 2),
        "capacidad_m3": (10, 2),
        "rendimiento_km_l": (10, 3),
        "factor_co2_kg_km": (10, 5),
    }
    for name, precision in expected_numeric.items():
        column_type = table.c[name].type
        assert isinstance(column_type, Numeric)
        assert (column_type.precision, column_type.scale) == precision

    assert {constraint.name for constraint in table.constraints if constraint.name} == (
        EXPECTED_CONSTRAINTS
    )
    assert {index.name for index in table.indexes} == {"ix_vehiculo_estado"}
    assert all(isinstance(index, Index) for index in table.indexes)
    plate_check = next(
        constraint
        for constraint in table.constraints
        if constraint.name == "ck_vehiculo_placa_canonica"
    )
    assert str(plate_check.sqltext) == EXPECTED_PLATE_CHECK
    model_checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if constraint.name in EXPECTED_NUMERIC_CHECKS
    }
    assert model_checks == EXPECTED_NUMERIC_CHECKS


def test_vehicle_type_catalog_matches_model_and_migration(monkeypatch):
    assert TIPOS_VEHICULO == EXPECTED_TYPES
    model_constraint = next(
        constraint
        for constraint in Vehiculo.__table__.constraints
        if constraint.name == "ck_vehiculo_tipo"
    )
    assert _check_values(model_constraint) == EXPECTED_TYPES

    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0004_create_vehiculo.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    created_objects = []
    monkeypatch.setattr(
        migration.op,
        "create_table",
        lambda table_name, *objects: created_objects.extend(objects),
    )
    monkeypatch.setattr(migration.op, "create_index", lambda *args, **kwargs: None)
    migration.upgrade()
    migration_constraint = next(
        constraint
        for constraint in created_objects
        if isinstance(constraint, CheckConstraint)
        and constraint.name == "ck_vehiculo_tipo"
    )
    assert _check_values(migration_constraint) == EXPECTED_TYPES
    migration_plate_check = next(
        constraint
        for constraint in created_objects
        if isinstance(constraint, CheckConstraint)
        and constraint.name == "ck_vehiculo_placa_canonica"
    )
    assert str(migration_plate_check.sqltext) == EXPECTED_PLATE_CHECK
    migration_numeric_checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in created_objects
        if isinstance(constraint, CheckConstraint)
        and constraint.name in EXPECTED_NUMERIC_CHECKS
    }
    assert migration_numeric_checks == EXPECTED_NUMERIC_CHECKS
