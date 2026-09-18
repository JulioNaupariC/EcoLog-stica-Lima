"""Import models to register their Alembic metadata."""

from app.models.auditoria import Auditoria
from app.models.usuario import Usuario

__all__ = ["Auditoria", "Usuario"]
