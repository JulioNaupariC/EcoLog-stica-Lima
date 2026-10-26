"""Private credential persistence boundary; callers own the transaction."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.usuario import Usuario


class CredentialStorageError(RuntimeError):
    """Sanitized storage failure; caller must roll back the transaction."""


@dataclass(frozen=True)
class UserIdentity:
    usuario_id: UUID
    email: str
    rol: str
    estado: str
    creado_en: datetime


@dataclass(frozen=True, repr=False)
class LoginAccount:
    usuario_id: UUID
    rol: str
    estado: str
    intentos_fallidos: int
    bloqueado_hasta: datetime | None
    debe_cambiar_contrasena: bool = False
    contrasena_temporal_expira_en: datetime | None = None


@dataclass(frozen=True)
class UserSummary:
    """Administrative projection; the password hash is never selected."""

    usuario_id: UUID
    email: str
    rol: str
    estado: str
    debe_cambiar_contrasena: bool


def _login_account(usuario: Usuario) -> LoginAccount:
    return LoginAccount(
        usuario.usuario_id,
        usuario.rol,
        usuario.estado,
        usuario.intentos_fallidos,
        usuario.bloqueado_hasta,
        usuario.debe_cambiar_contrasena,
        usuario.contrasena_temporal_expira_en,
    )


class UsuarioRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _insert(self, usuario: Usuario) -> UserIdentity:
        try:
            self._session.add(usuario)
            self._session.flush()
            return UserIdentity(
                usuario.usuario_id,
                usuario.email,
                usuario.rol,
                usuario.estado,
                usuario.creado_en,
            )
        except SQLAlchemyError:
            raise CredentialStorageError("Credential storage unavailable") from None

    def _verify_and_rehash(
        self, usuario_id: UUID, password: str, *, rehash: bool
    ) -> bool:
        # Imports keep all cryptography in the single password adapter.
        from app.core.passwords import hash_password, needs_rehash, verify_password

        try:
            stored_hash = self._session.scalar(
                select(Usuario.password_hash).where(Usuario.usuario_id == usuario_id)
            )
            if stored_hash is None or not verify_password(password, stored_hash):
                return False
            if rehash and needs_rehash(stored_hash):
                new_hash = hash_password(password)
                # A concurrent credential change must not be overwritten.
                result = self._session.execute(
                    update(Usuario)
                    .where(
                        Usuario.usuario_id == usuario_id,
                        Usuario.password_hash == stored_hash,
                    )
                    .values(password_hash=new_hash)
                    .execution_options(synchronize_session=False)
                )
                return result.rowcount == 1
            return True
        except SQLAlchemyError:
            raise CredentialStorageError("Credential storage unavailable") from None

    def find_for_login(self, email: str) -> LoginAccount | None:
        try:
            usuario = self._session.scalar(
                select(Usuario).where(Usuario.email == email).with_for_update()
            )
            return None if usuario is None else _login_account(usuario)
        except SQLAlchemyError:
            raise CredentialStorageError("Credential storage unavailable") from None

    def find_by_id_for_update(self, usuario_id: UUID) -> LoginAccount | None:
        try:
            usuario = self._session.scalar(
                select(Usuario)
                .where(Usuario.usuario_id == usuario_id)
                .with_for_update()
            )
            return None if usuario is None else _login_account(usuario)
        except SQLAlchemyError:
            raise CredentialStorageError("Credential storage unavailable") from None

    def list_page(self, page: int, page_size: int) -> tuple[list[UserSummary], int]:
        try:
            total = self._session.scalar(select(func.count()).select_from(Usuario))
            rows = self._session.execute(
                select(
                    Usuario.usuario_id,
                    Usuario.email,
                    Usuario.rol,
                    Usuario.estado,
                    Usuario.debe_cambiar_contrasena,
                )
                .order_by(Usuario.email, Usuario.usuario_id)
                .limit(page_size)
                .offset((page - 1) * page_size)
            ).all()
            return [UserSummary(*row) for row in rows], int(total or 0)
        except SQLAlchemyError:
            raise CredentialStorageError("Credential storage unavailable") from None

    def _set_password(
        self,
        usuario_id: UUID,
        password_hash: str,
        *,
        debe_cambiar_contrasena: bool,
        contrasena_temporal_expira_en: datetime | None,
    ) -> None:
        # Only CredentialService calls this, always with a freshly computed hash.
        try:
            self._session.execute(
                update(Usuario)
                .where(Usuario.usuario_id == usuario_id)
                .values(
                    password_hash=password_hash,
                    debe_cambiar_contrasena=debe_cambiar_contrasena,
                    contrasena_temporal_expira_en=contrasena_temporal_expira_en,
                    intentos_fallidos=0,
                    bloqueado_hasta=None,
                )
            )
        except SQLAlchemyError:
            raise CredentialStorageError("Credential storage unavailable") from None

    def set_login_state(
        self,
        usuario_id: UUID,
        *,
        intentos_fallidos: int,
        bloqueado_hasta: datetime | None,
    ) -> None:
        try:
            self._session.execute(
                update(Usuario)
                .where(Usuario.usuario_id == usuario_id)
                .values(
                    intentos_fallidos=intentos_fallidos,
                    bloqueado_hasta=bloqueado_hasta,
                )
            )
        except SQLAlchemyError:
            raise CredentialStorageError("Credential storage unavailable") from None
