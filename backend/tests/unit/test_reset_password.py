"""ECL-78: scripts/reset_password.py and the shared guard, without a database."""

import io
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.auditoria import DetalleContrasena, Evento
from app.repositories.usuarios import LoginAccount
from scripts import reset_password as module
from scripts._guard import TargetRefused, ensure_safe_target
from scripts.reset_password import (
    ResetRefused,
    ensure_local_target,
    main,
    read_new_password,
    reset_password,
)

NEW = "nueva-contrasena-segura"
NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
URL = "postgresql+psycopg://user@127.0.0.1:5432/ecologistica_{}"


class Terminal(io.StringIO):
    def __init__(self, tty: bool) -> None:
        super().__init__()
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def answers(*values):
    prompt = Mock(side_effect=list(values))
    return prompt


# --- Guardián común ------------------------------------------------------


@pytest.mark.parametrize("suffix", ["demo", "local"])
def test_guard_accepts_allowed_suffixes_and_returns_name(suffix):
    name = ensure_safe_target(URL.format(suffix), "development", ("_demo", "_local"))
    assert name == f"ecologistica_{suffix}"


@pytest.mark.parametrize(
    "url,env,message",
    [
        (URL.format("demo"), " Production ", "APP_ENV=production"),
        (None, "development", "Falta DATABASE_URL"),
        ("no es una url", "development", "no es válida"),
        (URL.format("test"), "test", "'_demo' o '_local'"),
        ("postgresql+psycopg://user@127.0.0.1:5432/", None, "'_demo' o '_local'"),
    ],
)
def test_guard_refuses_with_the_requested_error(url, env, message):
    with pytest.raises(TargetRefused, match=message):
        ensure_safe_target(url, env, ("_demo", "_local"))


def test_guard_uses_custom_error_and_production_message():
    class Custom(RuntimeError):
        pass

    with pytest.raises(Custom, match="mensaje propio"):
        ensure_safe_target(
            URL.format("demo"),
            "production",
            ("_demo",),
            error=Custom,
            production_message="mensaje propio",
        )


@pytest.mark.parametrize("suffixes", [(), ("",)])
def test_guard_requires_explicit_suffixes(suffixes):
    with pytest.raises(ValueError):
        ensure_safe_target(URL.format("demo"), "development", suffixes)


def test_script_allows_demo_and_local_only():
    ensure_local_target(URL.format("demo"), "development")
    ensure_local_target(URL.format("local"), None)
    for url, env in ((URL.format("test"), "test"), (URL.format("local"), "production")):
        with pytest.raises(ResetRefused, match="no se modificó nada"):
            ensure_local_target(url, env)


# --- Lectura de la contraseña ------------------------------------------------


def test_reads_the_password_twice_on_a_terminal():
    prompt = answers(NEW, NEW)
    assert read_new_password(Terminal(tty=True), prompt) == NEW
    assert prompt.call_count == 2


def test_without_terminal_refuses_before_prompting():
    prompt = answers(NEW, NEW)
    with pytest.raises(ResetRefused, match="run -it"):
        read_new_password(Terminal(tty=False), prompt)
    prompt.assert_not_called()


@pytest.mark.parametrize(
    "first,second,message",
    [
        (NEW, NEW + "x", "no coinciden"),
        ("corta-11ch!", "corta-11ch!", "al menos 12"),
        ("", "", "al menos 12"),
    ],
)
def test_mismatch_or_short_password_is_refused_without_echo(first, second, message):
    with pytest.raises(ResetRefused, match=message) as error:
        read_new_password(Terminal(tty=True), answers(first, second))
    assert not first or first not in str(error.value)


def test_exactly_twelve_characters_is_accepted():
    value = "x" * 12
    assert read_new_password(Terminal(tty=True), answers(value, value)) == value


@pytest.mark.parametrize("interruption", [EOFError, KeyboardInterrupt])
def test_cancelled_prompt_is_refused(interruption):
    with pytest.raises(ResetRefused, match="cancelada"):
        read_new_password(Terminal(tty=True), Mock(side_effect=interruption))


# --- Transacción ---------------------------------------------------------------


@pytest.fixture
def fakes(monkeypatch):
    users = Mock()
    sessions = Mock()
    sessions.revoke_all_for_user.return_value = 2
    credentials = Mock()
    audit_rows = []
    audit = Mock()
    audit.insert.side_effect = audit_rows.append
    monkeypatch.setattr(module, "UsuarioRepository", lambda session: users)
    monkeypatch.setattr(module, "SesionRepository", lambda session: sessions)
    monkeypatch.setattr(module, "CredentialService", lambda repository: credentials)
    monkeypatch.setattr(module, "AuditoriaRepository", lambda session: audit)
    return SimpleNamespace(
        factory=MagicMock(),
        users=users,
        sessions=sessions,
        credentials=credentials,
        audit_rows=audit_rows,
    )


def account():
    return LoginAccount(uuid4(), "ADMINISTRADOR", "ACTIVO", 2, NOW, True, NOW)


def test_reset_replaces_hash_revokes_sessions_and_audits(fakes):
    target = account()
    fakes.users.find_for_login.return_value = target

    assert reset_password(fakes.factory, "a@example.test", NEW, now=NOW) == 2

    fakes.users.find_for_login.assert_called_once_with("a@example.test")
    fakes.credentials.replace.assert_called_once_with(target.usuario_id, NEW)
    fakes.sessions.revoke_all_for_user.assert_called_once_with(target.usuario_id, NOW)
    [row] = fakes.audit_rows
    assert row.evento is Evento.CONTRASENA_CAMBIADA
    assert row.usuario_id == row.entidad_id == target.usuario_id
    assert row.detalle == DetalleContrasena(sesiones_revocadas=2)
    assert NEW not in str(row.model_dump())
    fakes.factory.begin.assert_called_once()


def test_unknown_email_changes_nothing(fakes):
    fakes.users.find_for_login.return_value = None
    with pytest.raises(ResetRefused, match="No existe una cuenta") as error:
        reset_password(fakes.factory, "nadie@example.test", NEW)
    assert NEW not in str(error.value)
    fakes.credentials.replace.assert_not_called()
    fakes.sessions.revoke_all_for_user.assert_not_called()
    assert fakes.audit_rows == []


def test_storage_failure_is_sanitized(fakes):
    fakes.users.find_for_login.side_effect = SQLAlchemyError(f"private {NEW}")
    with pytest.raises(ResetRefused, match="No se pudo completar") as error:
        reset_password(fakes.factory, "a@example.test", NEW)
    assert NEW not in str(error.value) and "private" not in str(error.value)


# --- main ----------------------------------------------------------------------


@pytest.fixture
def demo_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL.format("demo"))
    return {"APP_ENV": "development"}


def test_main_happy_path_reports_without_the_password(demo_env, monkeypatch, capsys):
    dispose = Mock()
    factory = MagicMock()
    calls = []
    monkeypatch.setattr(
        module,
        "reset_password",
        lambda f, email, password: calls.append((f, email, password)) or 3,
    )
    code = main(
        ["--email", " admin.demo@ecologistica.example "],
        demo_env,
        stdin=Terminal(tty=True),
        prompt=answers(NEW, NEW),
        factory_builder=lambda settings: (factory, dispose),
    )
    out, err = capsys.readouterr()
    assert code == 0
    assert calls == [(factory, "admin.demo@ecologistica.example", NEW)]
    assert "sesiones revocadas: 3" in out
    assert NEW not in out + err
    dispose.assert_called_once()


@pytest.mark.parametrize(
    "database,app_env",
    [("demo", "production"), ("test", "development"), ("produccion", None)],
)
def test_main_unhappy_refuses_before_prompting_or_connecting(
    monkeypatch, capsys, database, app_env
):
    monkeypatch.setenv("DATABASE_URL", URL.format(database))
    prompt = answers(NEW, NEW)
    builder = Mock()
    environ = {} if app_env is None else {"APP_ENV": app_env}
    code = main(
        ["--email", "admin.demo@ecologistica.example"],
        environ,
        stdin=Terminal(tty=True),
        prompt=prompt,
        factory_builder=builder,
    )
    assert code == 2
    assert "no se modificó nada" in capsys.readouterr().err
    prompt.assert_not_called()
    builder.assert_not_called()


@pytest.mark.parametrize(
    "stdin,prompt,email,message",
    [
        (Terminal(tty=False), answers(NEW, NEW), "a@example.test", "run -it"),
        (Terminal(tty=True), answers(NEW, "otra"), "a@example.test", "no coinciden"),
        (Terminal(tty=True), answers("corta", "corta"), "a@example.test", "12"),
        (Terminal(tty=True), answers(NEW, NEW), "   ", "Indique el correo"),
    ],
)
def test_main_edge_cases_never_connect(demo_env, capsys, stdin, prompt, email, message):
    builder = Mock()
    code = main(
        ["--email", email],
        demo_env,
        stdin=stdin,
        prompt=prompt,
        factory_builder=builder,
    )
    out, err = capsys.readouterr()
    assert code == 2
    assert message in err
    assert NEW not in out + err
    builder.assert_not_called()


def test_main_unknown_email_disposes_engine_and_hides_password(
    demo_env, monkeypatch, capsys
):
    dispose = Mock()

    def refuse(factory, email, password):
        raise ResetRefused("No existe una cuenta con ese correo; no se modificó nada.")

    monkeypatch.setattr(module, "reset_password", refuse)
    code = main(
        ["--email", "nadie@example.test"],
        demo_env,
        stdin=Terminal(tty=True),
        prompt=answers(NEW, NEW),
        factory_builder=lambda settings: (MagicMock(), dispose),
    )
    out, err = capsys.readouterr()
    assert code == 2
    assert "No existe una cuenta" in err
    assert NEW not in out + err
    dispose.assert_called_once()


def test_build_factory_uses_the_configured_database(monkeypatch):
    engine = Mock()
    monkeypatch.setattr(module, "build_engine", lambda settings: engine)
    factory, dispose = module._build_factory(Mock())
    assert factory.kw["bind"] is engine
    assert dispose is engine.dispose


def test_email_is_required(capsys):
    with pytest.raises(SystemExit):
        main([], {})
    assert "--email" in capsys.readouterr().err
