"""Restablece la contraseña de una cuenta en una base local o de demo (ECL-78).

Uso (desde ``backend/``, en una terminal interactiva)::

    python -m scripts.reset_password --email administrador.demo@ecologistica.example

Sirve cuando se pierde la contraseña de una cuenta de demo, incluida la del
Administrador, que no puede restablecerse a sí mismo desde la aplicación.

* Solo corre contra bases cuyo nombre termine en ``_demo`` o ``_local`` y se
  niega con ``APP_ENV=production``.
* La contraseña nueva se pide dos veces con ``getpass``; nunca se recibe por
  argumento ni variable de entorno, ni se imprime o registra.
* En una sola transacción guarda el hash Argon2id, deja
  ``debe_cambiar_contrasena=false``, limpia el vencimiento temporal, los
  intentos y el bloqueo, revoca las sesiones activas de la cuenta y audita
  ``CONTRASENA_CAMBIADA`` sin la contraseña ni el hash.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import TextIO

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.passwords import MIN_PASSWORD_LENGTH, PasswordOperationError
from app.db.session import build_engine, session_factory
from app.repositories.auditoria import (
    AuditoriaRepository,
    AuditStorageError,
    DetalleContrasena,
    Evento,
    Registro,
)
from app.repositories.sesiones import SesionRepository, SessionStorageError
from app.repositories.usuarios import CredentialStorageError, UsuarioRepository
from app.services.credenciales import CredentialService
from scripts._guard import ensure_safe_target

ALLOWED_SUFFIXES = ("_demo", "_local")
UNCHANGED = "no se modificó nada."


class ResetRefused(RuntimeError):
    """The reset cannot proceed; the message never contains a password."""


def ensure_local_target(database_url: str | None, app_env: str | None) -> None:
    ensure_safe_target(
        database_url,
        app_env,
        ALLOWED_SUFFIXES,
        error=ResetRefused,
        production_message=f"No se restablecen contraseñas con APP_ENV=production; "
        f"{UNCHANGED}",
    )


def read_new_password(stdin: TextIO, prompt: Callable[[str], str]) -> str:
    """Ask twice on an interactive terminal; never echo or return a weak value."""
    if not stdin.isatty():
        raise ResetRefused(
            "Se necesita una terminal interactiva para escribir la contraseña "
            f"(en Docker, use 'run -it'); {UNCHANGED}"
        )
    try:
        first = prompt("Contraseña nueva (mínimo 12 caracteres): ")
        second = prompt("Repita la contraseña nueva: ")
    except (EOFError, KeyboardInterrupt):
        raise ResetRefused(f"Operación cancelada; {UNCHANGED}") from None
    if first != second:
        raise ResetRefused(f"Las contraseñas no coinciden; {UNCHANGED}")
    if len(first) < MIN_PASSWORD_LENGTH:
        raise ResetRefused(
            f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres; "
            f"{UNCHANGED}"
        )
    return first


def reset_password(
    factory: sessionmaker[Session],
    email: str,
    password: str,
    *,
    now: datetime | None = None,
) -> int:
    """Replace the password like the in-app change; return revoked sessions."""
    current = now or datetime.now(timezone.utc)
    try:
        with factory.begin() as session:
            users = UsuarioRepository(session)
            account = users.find_for_login(email)
            if account is None:
                raise ResetRefused(f"No existe una cuenta con ese correo; {UNCHANGED}")
            # Clears the reset flag, temporary expiry, attempts and lockout.
            CredentialService(users).replace(account.usuario_id, password)
            revoked = SesionRepository(session).revoke_all_for_user(
                account.usuario_id, current
            )
            # Same event as the in-app change; the actor is the account itself
            # because the script runs outside any application session.
            AuditoriaRepository(session).insert(
                Registro(
                    usuario_id=account.usuario_id,
                    entidad_id=account.usuario_id,
                    evento=Evento.CONTRASENA_CAMBIADA,
                    detalle=DetalleContrasena(sesiones_revocadas=revoked),
                )
            )
            return revoked
    except (
        CredentialStorageError,
        SessionStorageError,
        PasswordOperationError,
        AuditStorageError,
        SQLAlchemyError,
    ):
        raise ResetRefused(
            f"No se pudo completar el restablecimiento; {UNCHANGED}"
        ) from None


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.reset_password",
        description="Restablece la contraseña de una cuenta en una base "
        "*_demo o *_local. La contraseña se pide con getpass.",
    )
    parser.add_argument("--email", required=True, help="Correo de la cuenta")
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    environ: Mapping[str, str] = os.environ,
    *,
    stdin: TextIO | None = None,
    prompt: Callable[[str], str] = getpass.getpass,
    factory_builder: Callable[[Settings], tuple[sessionmaker[Session], Callable]]
    | None = None,
) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    email = args.email.strip()
    settings = Settings()
    database_url = (
        settings.database_url.get_secret_value() if settings.database_url else None
    )
    try:
        # Every check runs before asking for the password or connecting.
        ensure_local_target(database_url, environ.get("APP_ENV", settings.app_env))
        if not email:
            raise ResetRefused(f"Indique el correo de la cuenta; {UNCHANGED}")
        password = read_new_password(stdin or sys.stdin, prompt)
        factory, dispose = (factory_builder or _build_factory)(settings)
        try:
            revoked = reset_password(factory, email, password)
        finally:
            dispose()
    except ResetRefused as error:
        print(f"reset_password: {error}", file=sys.stderr)
        return 2
    print(
        f"reset_password: contraseña actualizada para {email}; "
        f"sesiones revocadas: {revoked}."
    )
    return 0


def _build_factory(settings: Settings) -> tuple[sessionmaker[Session], Callable]:
    engine = build_engine(settings)
    return session_factory(engine), engine.dispose


if __name__ == "__main__":
    sys.exit(main())
