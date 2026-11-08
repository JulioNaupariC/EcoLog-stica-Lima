"""EN-008 (ECL-26): versioned parameter use cases (RNF-011).

A new version never edits or deletes: it closes the open one at its own
``vigente_desde`` and is audited in the same transaction. ``conjunto`` returns
the exact values of a version so any result can be recalculated later.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.models.parametro import Parametro, ParametroVersion
from app.repositories.auditoria import (
    AuditoriaRepository,
    AuditStorageError,
    DetalleParametrosVersionados,
    Evento,
    Registro,
)
from app.repositories.parametros import (
    ParametroRepository,
    ParametroStorageError,
    ParametroVersionDuplicada,
)
from app.schemas.parametro import ValorParametro, VersionCreate, VersionResponse


class ParametrosNoEncontrados(LookupError):
    """No version for that date or code."""


class ParametrosConflicto(RuntimeError):
    """Duplicate code or a start not after the open version's start."""


class ParametrosUnavailable(RuntimeError):
    """Sanitized operational failure."""


@dataclass(frozen=True)
class ConjuntoParametros:
    version: str
    valores: dict[str, Decimal]


def _respuesta(version: ParametroVersion, valores: list[Parametro]) -> VersionResponse:
    return VersionResponse(
        version=version.version,
        vigente_desde=version.vigente_desde,
        vigente_hasta=version.vigente_hasta,
        nota=version.nota,
        valores=[
            ValorParametro(
                codigo=v.codigo, valor=v.valor, unidad=v.unidad, fuente=v.fuente
            )
            for v in valores
        ],
    )


class ParametroService:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def vigente(self, momento: datetime | None = None) -> VersionResponse:
        cuando = momento or datetime.now(timezone.utc)
        try:
            with self._factory() as session:
                repository = ParametroRepository(session)
                version = repository.vigente_en(cuando)
                if version is None:
                    raise ParametrosNoEncontrados("No parameter version in force")
                return _respuesta(version, repository.valores(version.version_id))
        except (ParametroStorageError, SQLAlchemyError):
            raise ParametrosUnavailable("Parameter service unavailable") from None

    def por_version(self, codigo: str) -> VersionResponse:
        try:
            with self._factory() as session:
                repository = ParametroRepository(session)
                version = repository.por_codigo(codigo)
                if version is None:
                    raise ParametrosNoEncontrados("Unknown parameter version")
                return _respuesta(version, repository.valores(version.version_id))
        except (ParametroStorageError, SQLAlchemyError):
            raise ParametrosUnavailable("Parameter service unavailable") from None

    def conjunto(self, codigo: str) -> ConjuntoParametros:
        """Values of one version, for the calculations (ST-047, US-009)."""
        version = self.por_version(codigo)
        return ConjuntoParametros(
            version.version, {v.codigo: v.valor for v in version.valores}
        )

    def registrar(self, payload: VersionCreate, actor: UUID) -> VersionResponse:
        try:
            with self._factory.begin() as session:
                repository = ParametroRepository(session)
                abierta = repository.abierta_para_cierre()
                if abierta is not None:
                    if payload.vigente_desde <= abierta.vigente_desde:
                        raise ParametrosConflicto("Start must follow the open version")
                    repository.cerrar(abierta.version_id, payload.vigente_desde)
                version = ParametroVersion(
                    version=payload.version,
                    vigente_desde=payload.vigente_desde,
                    creada_por=actor,
                    nota=payload.nota,
                )
                valores = [
                    Parametro(
                        codigo=v.codigo, valor=v.valor, unidad=v.unidad, fuente=v.fuente
                    )
                    for v in payload.valores
                ]
                repository.agregar(version, valores)
                AuditoriaRepository(session).insert(
                    Registro(
                        usuario_id=actor,
                        entidad_id=version.version_id,
                        evento=Evento.PARAMETROS_VERSIONADOS,
                        detalle=DetalleParametrosVersionados(
                            codigos=tuple(sorted(v.codigo for v in payload.valores)),
                            cierra_version_anterior=abierta is not None,
                        ),
                    )
                )
                return _respuesta(version, valores)
        except ParametroVersionDuplicada:
            raise ParametrosConflicto("Version code already exists") from None
        except (ParametroStorageError, AuditStorageError, SQLAlchemyError):
            raise ParametrosUnavailable("Parameter service unavailable") from None
