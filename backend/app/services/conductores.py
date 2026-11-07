"""Atomic driver/account registration and validated profile updates."""

from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy import RowMapping
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.passwords import PasswordOperationError, hash_password
from app.models.conductor import Conductor
from app.models.usuario import Usuario
from app.repositories.auditoria import (
    AuditoriaRepository,
    AuditStorageError,
    DetalleConductorActualizado,
    DetalleConductorRegistrado,
    Evento,
    Registro,
)
from app.repositories.conductores import ConductorRepository
from app.schemas.conductor import (
    ConductorCreate,
    ConductorData,
    ConductorListItem,
    ConductorPage,
    ConductorResponse,
    ConductorSummary,
    ConductorUpdate,
)

LIMA = ZoneInfo("America/Lima")
PROFILE_FIELDS = tuple(ConductorData.model_fields)


class ConductorNotFound(LookupError):
    """Driver does not exist."""


class ConductorConflict(ValueError):
    """An identifier is already registered."""


class ConductorInvalid(ValueError):
    """The complete resulting profile is invalid."""


class ConductorUnavailable(RuntimeError):
    """Sanitized persistence or password operation failure."""


def _translate_integrity(error: IntegrityError) -> None:
    constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    if constraint in (
        "uq_conductor_dni",
        "uq_usuario_email",
        "uq_conductor_usuario_id",
    ):
        raise ConductorConflict("Identificador ya registrado") from None
    raise ConductorUnavailable("Servicio no disponible") from None


def _eligible(
    estado: str,
    cuenta_rol: str | None,
    cuenta_estado: str | None,
    licencia_vigente_hasta: date,
    disponible_desde: datetime | None,
    disponible_hasta: datetime | None,
) -> bool:
    now = datetime.now(LIMA)
    return bool(
        estado == "ACTIVO"
        and cuenta_rol == "CONDUCTOR"
        and cuenta_estado == "ACTIVO"
        and licencia_vigente_hasta >= now.date()
        and disponible_desde is not None
        and disponible_hasta is not None
        and disponible_hasta > now
    )


def _response(driver: Conductor, account: Usuario | None) -> ConductorResponse:
    eligible = _eligible(
        driver.estado,
        account.rol if account is not None else None,
        account.estado if account is not None else None,
        driver.licencia_vigente_hasta,
        driver.disponible_desde,
        driver.disponible_hasta,
    )
    return ConductorResponse(
        conductor_id=driver.conductor_id,
        usuario_id=driver.usuario_id,
        estado=driver.estado,
        habilitado_asignacion=eligible,
        **{field: getattr(driver, field) for field in PROFILE_FIELDS},
    )


def _list_item(row: RowMapping) -> ConductorListItem:
    return ConductorListItem(
        conductor_id=row["conductor_id"],
        nombre=row["nombre"],
        disponible_desde=row["disponible_desde"],
        disponible_hasta=row["disponible_hasta"],
        estado=row["estado"],
        habilitado_asignacion=_eligible(
            row["estado"],
            row["cuenta_rol"],
            row["cuenta_estado"],
            row["licencia_vigente_hasta"],
            row["disponible_desde"],
            row["disponible_hasta"],
        ),
    )


class ConductorService:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def create(self, payload: ConductorCreate, actor_id: UUID) -> ConductorSummary:
        try:
            # Hashing is centralized in the existing Argon2id adapter.
            encoded = hash_password(payload.password.get_secret_value())
            with self._factory.begin() as session:
                account = Usuario(
                    email=payload.email,
                    password_hash=encoded,
                    rol="CONDUCTOR",
                    estado="ACTIVO",
                )
                session.add(account)
                session.flush()
                driver = Conductor(
                    usuario_id=account.usuario_id,
                    estado="ACTIVO",
                    **payload.model_dump(include=set(PROFILE_FIELDS), mode="python"),
                )
                ConductorRepository(session).add(driver)
                # RN-015: same transaction, so the driver is not stored unaudited.
                AuditoriaRepository(session).insert(
                    Registro(
                        usuario_id=actor_id,
                        entidad_id=driver.conductor_id,
                        evento=Evento.CONDUCTOR_REGISTRADO,
                        detalle=DetalleConductorRegistrado(),
                    )
                )
                return ConductorSummary.model_validate(
                    _response(driver, account).model_dump()
                )
        except IntegrityError as error:
            _translate_integrity(error)
        except (SQLAlchemyError, PasswordOperationError, AuditStorageError):
            raise ConductorUnavailable("Servicio no disponible") from None

    def get(self, driver_id: UUID) -> ConductorResponse:
        try:
            with self._factory() as session:
                driver = ConductorRepository(session).get(driver_id)
                if driver is None:
                    raise ConductorNotFound("Conductor no encontrado")
                return _response(driver, session.get(Usuario, driver.usuario_id))
        except SQLAlchemyError:
            raise ConductorUnavailable("Servicio no disponible") from None

    def list_page(self, page: int, page_size: int) -> ConductorPage:
        try:
            with self._factory() as session:
                rows, total = ConductorRepository(session).list_page(page, page_size)
                items = [_list_item(row) for row in rows]
                return ConductorPage(
                    items=items, page=page, page_size=page_size, total=total
                )
        except SQLAlchemyError:
            raise ConductorUnavailable("Servicio no disponible") from None

    def update(
        self, driver_id: UUID, payload: ConductorUpdate, actor_id: UUID
    ) -> ConductorResponse:
        try:
            with self._factory.begin() as session:
                driver = ConductorRepository(session).get(driver_id, lock=True)
                if driver is None:
                    raise ConductorNotFound("Conductor no encontrado")
                values = {field: getattr(driver, field) for field in PROFILE_FIELDS}
                changes = payload.model_dump(exclude_unset=True, mode="python")
                values.update(changes)
                # Validate before mutating the ORM; rollback on any failure.
                try:
                    ConductorData.model_validate(values)
                except ValidationError:
                    raise ConductorInvalid("Perfil inválido") from None
                modified = tuple(
                    field
                    for field in PROFILE_FIELDS
                    if field in changes and getattr(driver, field) != changes[field]
                )
                for field, value in changes.items():
                    setattr(driver, field, value)
                session.flush()
                if modified:
                    # RN-015: audit field names only, never personal values.
                    AuditoriaRepository(session).insert(
                        Registro(
                            usuario_id=actor_id,
                            entidad_id=driver.conductor_id,
                            evento=Evento.CONDUCTOR_ACTUALIZADO,
                            detalle=DetalleConductorActualizado(
                                campos_modificados=modified
                            ),
                        )
                    )
                return _response(driver, session.get(Usuario, driver.usuario_id))
        except IntegrityError as error:
            _translate_integrity(error)
        except (SQLAlchemyError, AuditStorageError):
            raise ConductorUnavailable("Servicio no disponible") from None
