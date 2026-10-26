"""Framework-independent authorization; auditing must succeed before return."""

from collections.abc import Collection
from typing import Protocol
from uuid import UUID

from app.core.rbac import (
    Contexto,
    Decision,
    Identidad,
    Motivo,
    Permiso,
    Rol,
    evaluar,
)
from app.repositories.auditoria import Detalle, Evento, Registro


class AuditSink(Protocol):
    def registrar(self, registro: Registro) -> None: ...


class AuthorizationDenied(PermissionError):
    """Generic denial without identity, role or resource details."""


class AutorizacionService:
    def __init__(self, auditoria: AuditSink) -> None:
        self._auditoria = auditoria

    def autorizar(
        self,
        identidad: Identidad | None,
        permiso: Permiso,
        contexto: Contexto | None = None,
        *,
        entidad_id: UUID | None = None,
        roles: Collection[Rol] | None = None,
    ) -> Decision:
        decision = evaluar(identidad, permiso, contexto)
        # An endpoint may admit fewer roles than the global matrix grants the
        # permission to (e.g. ECL-73 I08); the matrix itself is not changed.
        if decision.permitido and roles is not None and identidad.rol not in roles:
            decision = Decision(False, Motivo.SIN_PERMISO)
        actor = (
            identidad.usuario_id
            if isinstance(identidad, Identidad)
            and isinstance(identidad.usuario_id, UUID)
            and decision.motivo not in (Motivo.IDENTIDAD_INVALIDA, Motivo.ROL_INVALIDO)
            else None
        )
        self._auditoria.registrar(
            Registro(
                usuario_id=actor,
                entidad_id=entidad_id,
                evento=Evento.PERMITIDA if decision.permitido else Evento.DENEGADA,
                detalle=Detalle(
                    permiso=permiso if isinstance(permiso, Permiso) else None,
                    motivo=decision.motivo,
                ),
            )
        )
        if not decision.permitido:
            raise AuthorizationDenied("Access denied")
        return decision
