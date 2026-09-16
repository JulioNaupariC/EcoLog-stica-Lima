from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models.usuario import Usuario


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
