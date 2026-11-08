"""ECL-79: public reasons for an unassigned driver; preserve history on rollback."""

import sqlalchemy as sa

from alembic import op

revision = "0018_motivos_elegibilidad"
down_revision = "0017_parametros_versionados"
branch_labels = None
depends_on = None

_OLD = ("SIN_CONDUCTOR_ELEGIBLE",)
_NEW = (*_OLD, "LICENCIA_VENCIDA", "DISPONIBILIDAD_INSUFICIENTE", "JORNADA_INVIABLE")
_CONSTRAINT = "ck_ruta_motivo_sin_conductor"


def _replace(values: tuple[str, ...]) -> None:
    quoted = ",".join(f"'{value}'" for value in values)
    op.drop_constraint(_CONSTRAINT, "ruta", type_="check")
    op.create_check_constraint(
        _CONSTRAINT,
        "ruta",
        f"motivo_sin_conductor IS NULL OR motivo_sin_conductor IN ({quoted})",
    )


def upgrade() -> None:
    _replace(_NEW)


def downgrade() -> None:
    # Never erase/replace a recorded operational reason to make a rollback pass.
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM ruta WHERE motivo_sin_conductor IS NOT NULL "
            "AND motivo_sin_conductor <> 'SIN_CONDUCTOR_ELEGIBLE')"
        )
    ):
        raise RuntimeError("ECL-79 reasons require manual treatment before downgrade")
    _replace(_OLD)
