"""Private credential persistence boundary; callers own the transaction."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
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
