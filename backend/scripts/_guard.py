"""Protección común de los scripts que escriben en una base local o de demo.

Antes de abrir una conexión, rechaza ``APP_ENV=production`` y cualquier base
cuyo nombre no termine en uno de los sufijos permitidos. Cada script decide los
sufijos, la excepción que se lanza y el mensaje para producción.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class TargetRefused(RuntimeError):
    """The target is not an explicit, non-production local or demo database."""


def ensure_safe_target(
    database_url: str | None,
    app_env: str | None,
    suffixes: Sequence[str],
    *,
    error: type[Exception] = TargetRefused,
    production_message: str = "No se permite con APP_ENV=production.",
) -> str:
    """Return the database name or raise ``error`` without touching anything."""
    if not suffixes or any(not suffix for suffix in suffixes):
        raise ValueError("At least one non-empty suffix is required")
    if (app_env or "").strip().lower() == "production":
        raise error(production_message)
    if not database_url:
        raise error("Falta DATABASE_URL.")
    try:
        name = make_url(database_url).database
    except (ArgumentError, ValueError):
        raise error("DATABASE_URL no es válida.") from None
    if not name or not name.endswith(tuple(suffixes)):
        allowed = " o ".join(f"'{suffix}'" for suffix in suffixes)
        raise error(
            f"La base de datos debe terminar en {allowed}; no se modificó nada."
        )
    return name
