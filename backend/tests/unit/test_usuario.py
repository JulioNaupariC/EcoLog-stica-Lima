import importlib.util
import re
from pathlib import Path

from sqlalchemy import CheckConstraint, UniqueConstraint

from app.core.rbac import Rol
from app.models.usuario import ROLES, Usuario

EXPECTED_ROLES = (
    "ADMINISTRADOR",
    "OPERADOR",
    "CONDUCTOR",
    "ANALISTA",
    "AUDITOR",
)


def _check_values(constraint: CheckConstraint) -> tuple[str, ...]:
    return tuple(re.findall(r"'([^']+)'", str(constraint.sqltext)))


def test_approved_schema_and_safe_representation():
    table = Usuario.__table__
    assert set(table.columns.keys()) == {
        "usuario_id",
        "email",
        "password_hash",
        "rol",
        "estado",
        "creado_en",
    }
    assert all(not column.nullable for column in table.columns)
    assert str(table.c.usuario_id.server_default.arg) == "gen_random_uuid()"
    assert table.c.email.type.length == 255
    assert table.c.password_hash.type.length == 255
    assert table.c.rol.type.length == 20
    assert table.c.estado.type.length == 15
    assert table.c.creado_en.type.timezone
    assert any(isinstance(c, UniqueConstraint) for c in table.constraints)
    assert len([c for c in table.constraints if isinstance(c, CheckConstraint)]) == 2
    assert "secret" not in repr(Usuario(password_hash="secret"))


def test_role_catalog_matches_model_and_initial_migration(monkeypatch):
    assert tuple(role.value for role in Rol) == EXPECTED_ROLES
    assert ROLES == EXPECTED_ROLES

    model_constraint = next(
        constraint
        for constraint in Usuario.__table__.constraints
        if constraint.name == "ck_usuario_rol"
    )
    assert _check_values(model_constraint) == EXPECTED_ROLES

    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0001_create_usuario.py"
    )
    spec = importlib.util.spec_from_file_location(
        "initial_usuario_migration", migration_path
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    created_objects = []
    monkeypatch.setattr(
        migration.op,
        "create_table",
        lambda table_name, *objects: created_objects.extend(objects),
    )

    migration.upgrade()

    migration_constraint = next(
        constraint
        for constraint in created_objects
        if isinstance(constraint, CheckConstraint)
        and constraint.name == "ck_usuario_rol"
    )
    assert _check_values(migration_constraint) == EXPECTED_ROLES
