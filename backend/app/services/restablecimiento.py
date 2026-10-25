"""ECL-77 administrator password reset and mandatory change, independent from HTTP."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.passwords import (
    MIN_PASSWORD_LENGTH,
    PasswordOperationError,
    generate_temporary_password,
)
from app.core.rbac import Identidad, Permiso
from app.repositories.auditoria import (
    AuditoriaRepository,
    AuditStorageError,
    DetalleContrasena,
    Evento,
    Registro,
)
from app.repositories.sesiones import SesionRepository, SessionStorageError
from app.repositories.usuarios import (
    CredentialStorageError,
    UserSummary,
    UsuarioRepository,
)
from app.services.auditoria import AuditoriaService
from app.services.autenticacion import (
    AuthenticatedSession,
    audit_failed_credentials,
    register_failed_attempt,
    temporary_password_expired,
)
from app.services.autorizacion import AutorizacionService
from app.services.credenciales import CredentialService

TEMPORARY_PASSWORD_TTL = timedelta(hours=24)


class UsuarioNoEncontrado(LookupError):
    """Target user does not exist."""


class UsuarioInactivo(ValueError):
    """An inactive account cannot receive a temporary password."""


class AutoRestablecimiento(ValueError):
    """Administrators change their own password, they do not reset it."""


class ContrasenaActualInvalida(PermissionError):
    """Current password did not verify; counted like a failed login."""


class ContrasenaNuevaInvalida(ValueError):
    """New password breaks the minimum policy; its value is never kept."""


class RestablecimientoUnavailable(RuntimeError):
    """Sanitized persistence, audit or password backend failure."""


@dataclass(frozen=True, repr=False)
class ContrasenaTemporal:
    """Returned once to the administrator; only its hash is persisted."""

    contrasena_temporal: str
    expira_en: datetime


@dataclass(frozen=True)
class PaginaUsuarios:
    items: list[UserSummary]
    page: int
    page_size: int
    total: int


_STORAGE_ERRORS = (
    CredentialStorageError,
    SessionStorageError,
    PasswordOperationError,
    AuditStorageError,
    SQLAlchemyError,
)


class RestablecimientoService:
    def __init__(
        self,
        business_factory: sessionmaker[Session],
        autorizacion: AutorizacionService,
        auditoria: AuditoriaService,
    ) -> None:
        self._business_factory = business_factory
        self._autorizacion = autorizacion
        self._auditoria = auditoria

    def listar(self, page: int, page_size: int) -> PaginaUsuarios:
        try:
            with self._business_factory() as session:
                items, total = UsuarioRepository(session).list_page(page, page_size)
        except _STORAGE_ERRORS:
            raise RestablecimientoUnavailable("Servicio no disponible") from None
        return PaginaUsuarios(items, page, page_size, total)

    def restablecer(
        self, admin: Identidad, usuario_id: UUID, *, now: datetime | None = None
    ) -> ContrasenaTemporal:
        # Raises AuthorizationDenied (audited) before touching the target account.
        self._autorizacion.autorizar(
            admin, Permiso.USUARIOS_ACTUALIZAR, entidad_id=usuario_id
        )
        if admin.usuario_id == usuario_id:
            raise AutoRestablecimiento("Use the password change instead")
        current = now or datetime.now(timezone.utc)
        expires = current + TEMPORARY_PASSWORD_TTL
        temporary = generate_temporary_password()
        try:
            with self._business_factory.begin() as session:
                users = UsuarioRepository(session)
                account = users.find_by_id_for_update(usuario_id)
                if account is None:
                    raise UsuarioNoEncontrado("Usuario no encontrado")
                if account.estado == "INACTIVO":
                    raise UsuarioInactivo("Usuario inactivo")
                # Also clears failed attempts and any temporary lockout.
                CredentialService(users).set_temporary(usuario_id, temporary, expires)
                revoked = SesionRepository(session).revoke_all_for_user(
                    usuario_id, current
                )
                # RN-015: same transaction, so no reset is stored unaudited.
                AuditoriaRepository(session).insert(
                    Registro(
                        usuario_id=admin.usuario_id,
                        entidad_id=usuario_id,
                        evento=Evento.CONTRASENA_RESTABLECIDA,
                        detalle=DetalleContrasena(sesiones_revocadas=revoked),
                    )
                )
        except _STORAGE_ERRORS:
            raise RestablecimientoUnavailable("Servicio no disponible") from None
        return ContrasenaTemporal(temporary, expires)

    def cambiar(
        self,
        sesion: AuthenticatedSession,
        contrasena_actual: str,
        contrasena_nueva: str,
        *,
        now: datetime | None = None,
    ) -> None:
        if len(contrasena_nueva) < MIN_PASSWORD_LENGTH:
            raise ContrasenaNuevaInvalida("Password too short")
        if contrasena_nueva == contrasena_actual:
            raise ContrasenaNuevaInvalida("Password must change")
        current = now or datetime.now(timezone.utc)
        usuario_id = sesion.identidad.usuario_id
        blocked = False
        verified = False
        try:
            with self._business_factory.begin() as session:
                users = UsuarioRepository(session)
                account = users.find_by_id_for_update(usuario_id)
                if account is None:
                    raise ContrasenaActualInvalida("Invalid current password")
                credentials = CredentialService(users)
                verified = credentials.verify(
                    usuario_id, contrasena_actual
                ) and not temporary_password_expired(
                    account.debe_cambiar_contrasena,
                    account.contrasena_temporal_expira_en,
                    current,
                )
                if not verified:
                    # Committed on purpose: the attempt counts even though we fail.
                    blocked = register_failed_attempt(
                        users, usuario_id, account.intentos_fallidos, current
                    )
                else:
                    credentials.replace(usuario_id, contrasena_nueva)
                    revoked = SesionRepository(session).revoke_all_for_user(
                        usuario_id, current, except_sesion_id=sesion.sesion_id
                    )
                    AuditoriaRepository(session).insert(
                        Registro(
                            usuario_id=usuario_id,
                            entidad_id=usuario_id,
                            evento=Evento.CONTRASENA_CAMBIADA,
                            detalle=DetalleContrasena(sesiones_revocadas=revoked),
                        )
                    )
            if not verified:
                audit_failed_credentials(self._auditoria, usuario_id, blocked)
        except _STORAGE_ERRORS:
            raise RestablecimientoUnavailable("Servicio no disponible") from None
        if not verified:
            raise ContrasenaActualInvalida("Invalid current password")
