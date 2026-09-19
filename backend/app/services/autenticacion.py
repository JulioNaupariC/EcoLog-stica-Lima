"""Login and opaque-session orchestration, independent from HTTP."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.passwords import PasswordOperationError, verify_password
from app.core.rbac import Identidad, Rol
from app.core.session_tokens import generate_session_token, hash_session_token
from app.repositories.auditoria import (
    AuditStorageError,
    DetalleAcceso,
    Evento,
    Registro,
    ResultadoAcceso,
)
from app.repositories.sesiones import SesionRepository, SessionStorageError
from app.repositories.usuarios import CredentialStorageError, UsuarioRepository
from app.services.auditoria import AuditoriaService
from app.services.credenciales import CredentialService


class InvalidCredentials(PermissionError):
    """Public authentication denial with no account details."""


class InvalidSession(PermissionError):
    """Missing, expired, revoked or currently ineligible session."""


class AuthenticationUnavailable(RuntimeError):
    """Sanitized operational authentication failure."""


@dataclass(frozen=True, repr=False)
class LoginResult:
    token: str
    sesion_id: UUID
    identidad: Identidad
    expira_en: datetime


@dataclass(frozen=True, repr=False)
class AuthenticatedSession:
    sesion_id: UUID
    identidad: Identidad


_DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$YMvBhc4xzf5ij+Th1Fwjew$"
    "ap73O8DrnvjLYxaLuR0Rqjumr51oJG9PaE/At4Vak2M"
)


class AutenticacionService:
    def __init__(
        self,
        business_factory: sessionmaker[Session],
        auditoria: AuditoriaService,
        *,
        ttl_minutes: int,
    ) -> None:
        self._business_factory = business_factory
        self._auditoria = auditoria
        self._ttl = timedelta(minutes=ttl_minutes)

    def login(
        self, email: str, password: str, *, now: datetime | None = None
    ) -> LoginResult:
        current = now or datetime.now(timezone.utc)
        account_id = None
        blocked = False
        result = None
        try:
            with self._business_factory.begin() as session:
                users = UsuarioRepository(session)
                account = users.find_for_login(email)
                if account is None:
                    verify_password(password, _DUMMY_PASSWORD_HASH)
                else:
                    account_id = account.usuario_id
                    attempts = account.intentos_fallidos
                    blocked_until = account.bloqueado_hasta
                    if blocked_until is not None and blocked_until <= current:
                        attempts = 0
                        blocked_until = None
                        users.set_login_state(
                            account.usuario_id,
                            intentos_fallidos=0,
                            bloqueado_hasta=None,
                        )
                    password_ok = CredentialService(users).verify_and_rehash(
                        account.usuario_id, password
                    )
                    eligible = account.estado == "ACTIVO" and (
                        blocked_until is None or blocked_until <= current
                    )
                    if password_ok and eligible:
                        users.set_login_state(
                            account.usuario_id,
                            intentos_fallidos=0,
                            bloqueado_hasta=None,
                        )
                        token = generate_session_token()
                        expires = current + self._ttl
                        session_id = SesionRepository(session).create(
                            account.usuario_id,
                            hash_session_token(token),
                            expires,
                        )
                        result = LoginResult(
                            token,
                            session_id,
                            Identidad(
                                account.usuario_id, Rol(account.rol), account.estado
                            ),
                            expires,
                        )
                    elif eligible:
                        attempts = min(attempts + 1, 3)
                        blocked = attempts == 3
                        users.set_login_state(
                            account.usuario_id,
                            intentos_fallidos=attempts,
                            bloqueado_hasta=(
                                current + timedelta(minutes=15) if blocked else None
                            ),
                        )
        except (
            CredentialStorageError,
            PasswordOperationError,
            SessionStorageError,
            SQLAlchemyError,
        ):
            raise AuthenticationUnavailable("Authentication unavailable") from None

        if result is None:
            try:
                self._audit(
                    Evento.LOGIN_FALLIDO,
                    ResultadoAcceso.CREDENCIALES_INVALIDAS,
                    entidad_id=account_id,
                )
                if blocked:
                    self._audit(
                        Evento.CUENTA_BLOQUEADA,
                        ResultadoAcceso.LIMITE_INTENTOS,
                        entidad_id=account_id,
                    )
            except AuditStorageError:
                raise AuthenticationUnavailable("Authentication unavailable") from None
            raise InvalidCredentials("Invalid credentials")

        try:
            self._audit(
                Evento.LOGIN_EXITOSO,
                ResultadoAcceso.EXITOSO,
                usuario_id=result.identidad.usuario_id,
                entidad_id=result.sesion_id,
            )
        except AuditStorageError:
            self._compensate_session(result.sesion_id, current)
            raise AuthenticationUnavailable("Authentication unavailable") from None
        return result

    def resolve(
        self, token: str, *, now: datetime | None = None
    ) -> AuthenticatedSession:
        current = now or datetime.now(timezone.utc)
        try:
            digest = hash_session_token(token)
            with self._business_factory() as session:
                found = SesionRepository(session).find_identity(digest)
        except ValueError:
            raise InvalidSession("Invalid session") from None
        except (SessionStorageError, SQLAlchemyError):
            raise AuthenticationUnavailable("Authentication unavailable") from None
        if (
            found is None
            or found.revocada_en is not None
            or found.expira_en <= current
            or found.estado != "ACTIVO"
            or (found.bloqueado_hasta is not None and found.bloqueado_hasta > current)
        ):
            raise InvalidSession("Invalid session")
        try:
            role = Rol(found.rol)
        except (TypeError, ValueError):
            raise InvalidSession("Invalid session") from None
        return AuthenticatedSession(
            found.sesion_id,
            Identidad(found.usuario_id, role, found.estado),
        )

    def logout(
        self,
        authenticated: AuthenticatedSession,
        *,
        now: datetime | None = None,
    ) -> None:
        current = now or datetime.now(timezone.utc)
        try:
            with self._business_factory.begin() as session:
                SesionRepository(session).revoke(authenticated.sesion_id, current)
            self._audit(
                Evento.SESION_CERRADA,
                ResultadoAcceso.CIERRE,
                usuario_id=authenticated.identidad.usuario_id,
                entidad_id=authenticated.sesion_id,
            )
        except (SessionStorageError, SQLAlchemyError, AuditStorageError):
            raise AuthenticationUnavailable("Authentication unavailable") from None

    def _compensate_session(self, session_id: UUID, current: datetime) -> None:
        try:
            with self._business_factory.begin() as session:
                SesionRepository(session).revoke(session_id, current)
        except (SessionStorageError, SQLAlchemyError):
            raise AuthenticationUnavailable("Authentication unavailable") from None

    def _audit(
        self,
        event: Evento,
        result: ResultadoAcceso,
        *,
        usuario_id: UUID | None = None,
        entidad_id: UUID | None = None,
    ) -> None:
        self._auditoria.registrar(
            Registro(
                usuario_id=usuario_id,
                entidad_id=entidad_id,
                evento=event,
                detalle=DetalleAcceso(resultado=result),
            )
        )
