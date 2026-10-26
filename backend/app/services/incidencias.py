"""ECL-73 incident registration and pending list, independent from HTTP."""

from datetime import datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.incidencias import (
    OCURRIDA_MAX_ANTIGUEDAD,
    OCURRIDA_MAX_FUTURO,
    EstadoIncidencia,
)
from app.models.incidencia import Incidencia
from app.repositories.auditoria import (
    AuditoriaRepository,
    AuditStorageError,
    DetalleIncidenciaRegistrada,
    Evento,
    Registro,
)
from app.repositories.incidencias import (
    IncidenciaDuplicateOperation,
    IncidenciaRepository,
    IncidenciaStorageError,
    StoredIncidencia,
)
from app.schemas.incidencia import (
    ConductorResumen,
    IncidenciaCreate,
    IncidenciaListItem,
    IncidenciaPage,
    IncidenciaRegistrada,
)

LIMA = ZoneInfo("America/Lima")
# Coordinates are compared to 1e-7 degrees (about 1 cm) for idempotency.
_COORDINATE_DIGITS = 7


class IncidenciaSinConductor(PermissionError):
    """The authenticated user has no driver profile."""


class IncidenciaInvalida(ValueError):
    """Out-of-window time or a stop that is not the driver's; no input echoed."""


class IncidenciaConflicto(ValueError):
    """Same operation_id with different content."""


class IncidenciaUnavailable(RuntimeError):
    """Sanitized persistence or audit failure."""


def _ack(stored: StoredIncidencia) -> IncidenciaRegistrada:
    return IncidenciaRegistrada(
        incidencia_id=stored.incidencia_id,
        operation_id=stored.operation_id,
        estado=EstadoIncidencia(stored.estado),
        registrada_en=stored.registrada_en.astimezone(LIMA),
    )


def _same_content(
    stored: StoredIncidencia, conductor_id: UUID, payload: IncidenciaCreate
) -> bool:
    return (
        stored.conductor_id == conductor_id
        and stored.tipo == payload.tipo.value
        and stored.severidad == payload.severidad.value
        and stored.ocurrida_en == payload.ocurrida_en
        and round(stored.latitud, _COORDINATE_DIGITS)
        == round(payload.latitud, _COORDINATE_DIGITS)
        and round(stored.longitud, _COORDINATE_DIGITS)
        == round(payload.longitud, _COORDINATE_DIGITS)
        and stored.parada_id == payload.parada_id
        and stored.observacion == payload.observacion
    )


class IncidenciaService:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def registrar(
        self,
        usuario_id: UUID,
        payload: IncidenciaCreate,
        *,
        now: datetime | None = None,
    ) -> tuple[IncidenciaRegistrada, bool]:
        """Return the acknowledgement and whether it was created now."""
        current = now or datetime.now(timezone.utc)
        try:
            with self._factory.begin() as session:
                repository = IncidenciaRepository(session)
                conductor_id = repository.conductor_id_for(usuario_id)
                if conductor_id is None:
                    raise IncidenciaSinConductor("No driver profile")
                # Idempotency first: a late retry from the offline queue keeps
                # its original answer even after the time window has passed.
                stored = repository.find_by_operation(payload.operation_id)
                if stored is not None:
                    if not _same_content(stored, conductor_id, payload):
                        raise IncidenciaConflicto("Operation ID conflict")
                    return _ack(stored), False
                self._validate(repository, usuario_id, payload, current)
                incidencia = repository.add(
                    Incidencia(
                        conductor_id=conductor_id,
                        parada_id=payload.parada_id,
                        operation_id=payload.operation_id,
                        tipo=payload.tipo.value,
                        severidad=payload.severidad.value,
                        ocurrida_en=payload.ocurrida_en,
                        observacion=payload.observacion,
                    ),
                    payload.latitud,
                    payload.longitud,
                )
                # RN-015: same transaction, so no incident is stored unaudited.
                AuditoriaRepository(session).insert(
                    Registro(
                        usuario_id=usuario_id,
                        entidad_id=incidencia.incidencia_id,
                        evento=Evento.INCIDENCIA_REGISTRADA,
                        detalle=DetalleIncidenciaRegistrada(
                            tipo=payload.tipo,
                            severidad=payload.severidad,
                            con_parada=payload.parada_id is not None,
                            con_observacion=payload.observacion is not None,
                        ),
                    )
                )
                return (
                    IncidenciaRegistrada(
                        incidencia_id=incidencia.incidencia_id,
                        operation_id=incidencia.operation_id,
                        estado=EstadoIncidencia(incidencia.estado),
                        registrada_en=incidencia.registrada_en.astimezone(LIMA),
                    ),
                    True,
                )
        except IncidenciaDuplicateOperation:
            return self._concurrent_retry(usuario_id, payload), False
        except (IncidenciaStorageError, AuditStorageError, SQLAlchemyError):
            raise IncidenciaUnavailable("Servicio no disponible") from None

    def listar(
        self, estado: EstadoIncidencia, page: int, page_size: int
    ) -> IncidenciaPage:
        try:
            with self._factory() as session:
                rows, total = IncidenciaRepository(session).list_page(
                    estado.value, page, page_size
                )
        except (IncidenciaStorageError, SQLAlchemyError):
            raise IncidenciaUnavailable("Servicio no disponible") from None
        return IncidenciaPage(
            items=[
                IncidenciaListItem(
                    incidencia_id=row.incidencia_id,
                    tipo=row.tipo,
                    severidad=row.severidad,
                    ocurrida_en=row.ocurrida_en.astimezone(LIMA),
                    registrada_en=row.registrada_en.astimezone(LIMA),
                    conductor=ConductorResumen(
                        conductor_id=row.conductor_id, nombre=row.nombre
                    ),
                    latitud=row.latitud,
                    longitud=row.longitud,
                    observacion=row.observacion,
                    estado=row.estado,
                )
                for row in rows
            ],
            page=page,
            page_size=page_size,
            total=total,
        )

    @staticmethod
    def _validate(
        repository: IncidenciaRepository,
        usuario_id: UUID,
        payload: IncidenciaCreate,
        current: datetime,
    ) -> None:
        if payload.ocurrida_en > current + OCURRIDA_MAX_FUTURO:
            raise IncidenciaInvalida("ocurrida_en in the future")
        if payload.ocurrida_en < current - OCURRIDA_MAX_ANTIGUEDAD:
            raise IncidenciaInvalida("ocurrida_en too old")
        if payload.parada_id is not None and not repository.stop_belongs_to(
            payload.parada_id, usuario_id
        ):
            raise IncidenciaInvalida("Stop is not assigned to the driver")

    def _concurrent_retry(
        self, usuario_id: UUID, payload: IncidenciaCreate
    ) -> IncidenciaRegistrada:
        """Another request stored the operation first: compare like a retry."""
        try:
            with self._factory() as session:
                repository = IncidenciaRepository(session)
                conductor_id = repository.conductor_id_for(usuario_id)
                stored = repository.find_by_operation(payload.operation_id)
        except (IncidenciaStorageError, SQLAlchemyError):
            raise IncidenciaUnavailable("Servicio no disponible") from None
        if stored is None or conductor_id is None:
            raise IncidenciaUnavailable("Servicio no disponible")
        if not _same_content(stored, conductor_id, payload):
            raise IncidenciaConflicto("Operation ID conflict")
        return _ack(stored)
