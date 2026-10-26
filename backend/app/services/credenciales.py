"""Internal credential provisioning and verification, without session or RBAC."""

from datetime import datetime
from uuid import UUID

from app.core.passwords import CredentialError, _validate_password, hash_password
from app.models.usuario import ROLES, Usuario
from app.repositories.usuarios import UserIdentity, UsuarioRepository


class CredentialService:
    def __init__(self, repository: UsuarioRepository) -> None:
        self._repository = repository

    def create(self, email: str, password: str, rol: str) -> UserIdentity:
        if not isinstance(email, str) or not email or len(email) > 255:
            raise CredentialError("Invalid credential input")
        if not isinstance(rol, str) or rol not in ROLES:
            raise CredentialError("Invalid credential input")
        # Every string is hashed, including strings resembling encoded hashes.
        # There is no public password_hash argument or hash passthrough.
        usuario = Usuario(email=email, password_hash=hash_password(password), rol=rol)
        return self._repository._insert(usuario)

    def verify(self, usuario_id: UUID, password: str) -> bool:
        _validate_password(password)
        return self._repository._verify_and_rehash(usuario_id, password, rehash=False)

    def verify_and_rehash(self, usuario_id: UUID, password: str) -> bool:
        """Only update after successful verification; caller commits explicitly."""
        _validate_password(password)
        return self._repository._verify_and_rehash(usuario_id, password, rehash=True)

    def set_temporary(
        self, usuario_id: UUID, password: str, expira_en: datetime
    ) -> None:
        """ECL-77: store only the hash of a temporary password that must change."""
        self._repository._set_password(
            usuario_id,
            hash_password(password),
            debe_cambiar_contrasena=True,
            contrasena_temporal_expira_en=expira_en,
        )

    def replace(self, usuario_id: UUID, password: str) -> None:
        """ECL-77: store the user's definitive password and clear the reset flag."""
        self._repository._set_password(
            usuario_id,
            hash_password(password),
            debe_cambiar_contrasena=False,
            contrasena_temporal_expira_en=None,
        )
