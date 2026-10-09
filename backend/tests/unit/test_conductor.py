"""Verify conductor ORM schema without a live database."""

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.models import Conductor


def test_conductor_metadata_matches_contract():
    table = Conductor.__table__
    assert table.name == "conductor"
    assert set(table.columns.keys()) == {
        "conductor_id",
        "usuario_id",
        "nombre",
        "dni",
        "licencia_numero",
        "licencia_vigente_hasta",
        "experiencia_anios",
        "telefono",
        "disponible_desde",
        "disponible_hasta",
        "punto_partida",
        "estado",
    }
    assert {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    } == {"uq_conductor_usuario_id", "uq_conductor_dni"}
    assert "fk_conductor_usuario_id_usuario" in {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    } == {
        "ck_conductor_dni_ocho_digitos",
        "ck_conductor_nombre",
        "ck_conductor_licencia",
        "ck_conductor_telefono_e164",
        "ck_conductor_punto_partida",
        "ck_conductor_experiencia",
        "ck_conductor_disponibilidad_intervalo",
        "ck_conductor_estado",
    }
    assert table.c.disponible_desde.nullable
    assert table.c.disponible_hasta.nullable
    assert not table.c.usuario_id.nullable


def test_repr_does_not_expose_personal_information():
    obj = Conductor(
        nombre="Nombre Privado",
        dni="01234567",
        telefono="+51987654321",
        licencia_numero="ABC123",
        punto_partida="Lugar Privado",
    )
    assert repr(obj) == "<Conductor>"
