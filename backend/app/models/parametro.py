"""EN-008 (ECL-26): versioned calculation parameters (RNF-011).

``parametro_version`` is one complete set with its validity window; only one
version is open (``vigente_hasta`` null). ``parametro`` holds each value with
its fixed unit and verifiable source. Rows are never updated or deleted: a
change is a new version.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.parametros import (
    FUENTE_MAX,
    NOTA_MAX,
    UNIDADES,
    VERSION_MAX,
    sql_in,
    unidad_valida_sql,
)
from app.db.base import Base


class ParametroVersion(Base):
    __tablename__ = "parametro_version"
    __table_args__ = (
        UniqueConstraint("version", name="uq_parametro_version_codigo"),
        CheckConstraint(
            "vigente_hasta IS NULL OR vigente_hasta > vigente_desde",
            name="ck_parametro_version_vigencia",
        ),
        CheckConstraint(
            "version ~ '^[A-Z0-9][A-Z0-9._-]*$'", name="ck_parametro_version_formato"
        ),
        # Exactly one open version at most.
        Index(
            "uq_parametro_version_abierta",
            text("(vigente_hasta IS NULL)"),
            unique=True,
            postgresql_where=text("vigente_hasta IS NULL"),
        ),
        Index("ix_parametro_version_vigencia", "vigente_desde"),
    )

    version_id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    version: Mapped[str] = mapped_column(String(VERSION_MAX))
    vigente_desde: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    vigente_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creada_por: Mapped[UUID] = mapped_column(
        ForeignKey(
            "usuario.usuario_id",
            name="fk_parametro_version_usuario",
            ondelete="RESTRICT",
        )
    )
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    nota: Mapped[str | None] = mapped_column(String(NOTA_MAX))

    def __repr__(self) -> str:
        return "<ParametroVersion>"


class Parametro(Base):
    __tablename__ = "parametro"
    __table_args__ = (
        UniqueConstraint(
            "version_id", "codigo", name="uq_parametro_version_codigo_valor"
        ),
        CheckConstraint(
            f"codigo IN ({sql_in(tuple(UNIDADES))})", name="ck_parametro_codigo"
        ),
        CheckConstraint(unidad_valida_sql(), name="ck_parametro_unidad"),
        CheckConstraint(
            "valor <> 'NaN'::numeric AND valor > 0", name="ck_parametro_valor"
        ),
        CheckConstraint("fuente ~ '[^[:space:]]'", name="ck_parametro_fuente"),
    )

    parametro_id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    version_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "parametro_version.version_id",
            name="fk_parametro_version",
            ondelete="RESTRICT",
        )
    )
    codigo: Mapped[str] = mapped_column(String(30))
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 9))
    unidad: Mapped[str] = mapped_column(String(20))
    fuente: Mapped[str] = mapped_column(String(FUENTE_MAX))

    def __repr__(self) -> str:
        return "<Parametro>"
