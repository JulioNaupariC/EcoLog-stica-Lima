"""Persistence boundary for opaque sessions; clear tokens are never accepted."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.sesion import Sesion
from app.models.usuario import Usuario


class SessionStorageError(RuntimeError):
    """Sanitized session storage failure."""


@dataclass(frozen=True, repr=False)
class SessionIdentity:
    sesion_id: UUID
    usuario_id: UUID
    rol: str
    estado: str
    bloqueado_hasta: datetime | None
    expira_en: datetime
    revocada_en: datetime | None
    debe_cambiar_contrasena: bool = False


class SesionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, usuario_id: UUID, token_hash: str, expira_en: datetime) -> UUID:
        try:
            row = Sesion(
                usuario_id=usuario_id, token_hash=token_hash, expira_en=expira_en
            )
            self._session.add(row)
            self._session.flush()
            return row.sesion_id
        except SQLAlchemyError:
            raise SessionStorageError("Session storage unavailable") from None

    def find_identity(self, token_hash: str) -> SessionIdentity | None:
        try:
            row = self._session.execute(
                select(Sesion, Usuario)
                .join(Usuario, Usuario.usuario_id == Sesion.usuario_id)
                .where(Sesion.token_hash == token_hash)
            ).one_or_none()
            if row is None:
                return None
            sesion, usuario = row
            return SessionIdentity(
                sesion.sesion_id,
                usuario.usuario_id,
                usuario.rol,
                usuario.estado,
                usuario.bloqueado_hasta,
                sesion.expira_en,
                sesion.revocada_en,
                usuario.debe_cambiar_contrasena,
            )
        except SQLAlchemyError:
            raise SessionStorageError("Session storage unavailable") from None

    def revoke(self, sesion_id: UUID, revoked_at: datetime) -> None:
        try:
            self._session.execute(
                update(Sesion)
                .where(Sesion.sesion_id == sesion_id, Sesion.revocada_en.is_(None))
                .values(revocada_en=revoked_at)
            )
        except SQLAlchemyError:
            raise SessionStorageError("Session storage unavailable") from None

    def revoke_all_for_user(
        self,
        usuario_id: UUID,
        revoked_at: datetime,
        *,
        except_sesion_id: UUID | None = None,
    ) -> int:
        """Revoke every active session of a user, optionally keeping one."""
        statement = update(Sesion).where(
            Sesion.usuario_id == usuario_id, Sesion.revocada_en.is_(None)
        )
        if except_sesion_id is not None:
            statement = statement.where(Sesion.sesion_id != except_sesion_id)
        try:
            result = self._session.execute(
                statement.values(revocada_en=revoked_at).execution_options(
                    synchronize_session=False
                )
            )
            return result.rowcount
        except SQLAlchemyError:
            raise SessionStorageError("Session storage unavailable") from None
