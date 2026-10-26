"""ECL-73 incident registration and pending list, independent from HTTP.

Rules from the ECL-72 BDD approved in PR #63. Order of checks: the schema and
RBAC run first (HTTP layer), then the driver profile, then idempotency per
(driver, operation_id), and only for a new operation the time tolerance and the
stop, so a changing stop context never invalidates an incident already stored.
"""

from datetime import datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.incidencias import OCURRIDA_MAX_FUTURO, EstadoIncidencia
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


def utc_now() -> datetime:
    """Server clock; integration tests fix it at T0 (I05, I14)."""
    return datetime.now(timezone.utc)


class IncidenciaSinConductor(PermissionError):
    """The authenticated user has no linked driver profile (403)."""


class IncidenciaParadaAjena(PermissionError):
    """The stop exists but belongs to another driver (generic 403, I10)."""


class IncidenciaInvalida(ValueError):
    """Future time beyond tolerance or a stop that does not exist (422)."""


class IncidenciaConflicto(ValueError):
    """Same driver and operation_id with different content (409, I11)."""


class IncidenciaUnavailable(RuntimeError):
    """Sanitized persistence or audit failure."""


def _ack(stored: StoredIncidencia) -> IncidenciaRegistrada:
    return IncidenciaRegistrada(
        incidencia_id=stored.incidencia_id,
        operation_id=stored.operation_id,
        estado=EstadoIncidencia(stored.estado),
        registrada_en=stored.registrada_en.astimezone(LIMA),
    )


def _equivalent(stored: StoredIncidencia, payload: IncidenciaCreate) -> bool:
    """I13: same UTC instant, numerically equal coordinates, exact text."""
    return (
        stored.tipo == payload.tipo.value
        and stored.severidad == payload.severidad.value
        and stored.ocurrida_en == payload.ocurrida_en
        and stored.latitud == payload.latitud
        and stored.longitud == payload.longitud
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
        current = now or utc_now()
        try:
            with self._factory.begin() as session:
                repository = IncidenciaRepository(session)
                conductor_id = repository.conductor_id_for(usuario_id)
                if conductor_id is None:
                    raise IncidenciaSinConductor("No driver profile")
                stored = repository.find_by_operation(
                    conductor_id, payload.operation_id
                )
                if stored is not None:
                    if not _equivalent(stored, payload):
                        raise IncidenciaConflicto("Operation ID conflict")
                    return _ack(stored), False
                self._validate_new(repository, usuario_id, payload, current)
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
                            con_observacion=payload.observacion != "",
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
            # I13: a concurrent first send won the race; never answer 5xx.
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
    def _validate_new(
        repository: IncidenciaRepository,
        usuario_id: UUID,
        payload: IncidenciaCreate,
        current: datetime,
    ) -> None:
        # Inclusive tolerance, compared as UTC instants; no maximum age (I05, I14).
        if payload.ocurrida_en > current + OCURRIDA_MAX_FUTURO:
            raise IncidenciaInvalida("ocurrida_en beyond the future tolerance")
        if payload.parada_id is not None:
            owner = repository.stop_owner(payload.parada_id)
            if owner is None:
                raise IncidenciaInvalida("Stop does not exist")
            if owner != usuario_id:
                raise IncidenciaParadaAjena("Stop belongs to another driver")

    def _concurrent_retry(
        self, usuario_id: UUID, payload: IncidenciaCreate
    ) -> IncidenciaRegistrada:
        """Re-read the winner of the race and compare it like a replay."""
        try:
            with self._factory() as session:
                repository = IncidenciaRepository(session)
                conductor_id = repository.conductor_id_for(usuario_id)
                stored = (
                    None
                    if conductor_id is None
                    else repository.find_by_operation(
                        conductor_id, payload.operation_id
                    )
                )
        except (IncidenciaStorageError, SQLAlchemyError):
            raise IncidenciaUnavailable("Servicio no disponible") from None
        if stored is None:
            raise IncidenciaUnavailable("Servicio no disponible")
        if not _equivalent(stored, payload):
            raise IncidenciaConflicto("Operation ID conflict")
        return _ack(stored)
