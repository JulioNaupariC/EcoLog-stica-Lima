"""EN-008 (ECL-26): storage of versioned parameters. Insert-only."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.parametro import Parametro, ParametroVersion


class ParametroStorageError(RuntimeError):
    """Sanitized parameter storage failure."""


class ParametroVersionDuplicada(RuntimeError):
    """The version code already exists."""


class ParametroRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def vigente_en(self, momento: datetime) -> ParametroVersion | None:
        try:
            return self._session.scalar(
                select(ParametroVersion)
                .where(ParametroVersion.vigente_desde <= momento)
                .where(
                    (ParametroVersion.vigente_hasta.is_(None))
                    | (ParametroVersion.vigente_hasta > momento)
                )
                .order_by(ParametroVersion.vigente_desde.desc())
                .limit(1)
            )
        except SQLAlchemyError:
            raise ParametroStorageError("Parameter storage unavailable") from None

    def por_codigo(self, version: str) -> ParametroVersion | None:
        try:
            return self._session.scalar(
                select(ParametroVersion).where(ParametroVersion.version == version)
            )
        except SQLAlchemyError:
            raise ParametroStorageError("Parameter storage unavailable") from None

    def valores(self, version_id: UUID) -> list[Parametro]:
        try:
            return list(
                self._session.scalars(
                    select(Parametro)
                    .where(Parametro.version_id == version_id)
                    .order_by(Parametro.codigo)
                ).all()
            )
        except SQLAlchemyError:
            raise ParametroStorageError("Parameter storage unavailable") from None

    def abierta_para_cierre(self) -> ParametroVersion | None:
        """The open version, locked so two registrations cannot both close it."""
        try:
            return self._session.scalar(
                select(ParametroVersion)
                .where(ParametroVersion.vigente_hasta.is_(None))
                .with_for_update()
            )
        except SQLAlchemyError:
            raise ParametroStorageError("Parameter storage unavailable") from None

    def cerrar(self, version_id: UUID, hasta: datetime) -> None:
        try:
            self._session.execute(
                update(ParametroVersion)
                .where(ParametroVersion.version_id == version_id)
                .values(vigente_hasta=hasta)
            )
        except SQLAlchemyError:
            raise ParametroStorageError("Parameter storage unavailable") from None

    def agregar(self, version: ParametroVersion, valores: list[Parametro]) -> None:
        try:
            self._session.add(version)
            self._session.flush()
            for valor in valores:
                valor.version_id = version.version_id
            self._session.add_all(valores)
            self._session.flush()
        except IntegrityError as error:
            if "uq_parametro_version_codigo" in str(error.orig):
                raise ParametroVersionDuplicada("Version already exists") from None
            raise ParametroStorageError("Parameter storage unavailable") from None
        except SQLAlchemyError:
            raise ParametroStorageError("Parameter storage unavailable") from None
