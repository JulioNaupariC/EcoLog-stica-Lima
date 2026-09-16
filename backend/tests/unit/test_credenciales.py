from dataclasses import asdict
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from argon2 import PasswordHasher
from sqlalchemy.exc import SQLAlchemyError

from app.core.passwords import CredentialError, hash_password, verify_password
from app.repositories.usuarios import (
    CredentialStorageError,
    UserIdentity,
    UsuarioRepository,
)
from app.services.credenciales import CredentialService


def test_create_hashes_before_persistence_and_returns_no_hash():
    session = MagicMock()

    def populate_defaults():
        user = session.add.call_args.args[0]
        user.usuario_id = uuid4()
        user.estado = "ACTIVO"
        user.creado_en = datetime.now(timezone.utc)

    session.flush.side_effect = populate_defaults
    service = CredentialService(UsuarioRepository(session))
    # Even an encoded hash supplied as a password is hashed again, never imported.
    password = hash_password("original")
    identity = service.create("test@example.test", password, "OPERADOR")
    user = session.add.call_args.args[0]
    assert user.password_hash != password
    assert verify_password(password, user.password_hash)
    assert isinstance(identity, UserIdentity)
    assert "password_hash" not in asdict(identity)
    assert password not in repr(identity)
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "email,password,rol",
    [
        (None, "password", "OPERADOR"),
        ("", "password", "OPERADOR"),
        ("a" * 256, "password", "OPERADOR"),
        ("a", "password", "INVALID"),
        ("a", "password", []),
        ("a", None, "OPERADOR"),
    ],
)
def test_invalid_create_does_not_persist(email, password, rol):
    repository = MagicMock()
    with pytest.raises(CredentialError):
        CredentialService(repository).create(email, password, rol)
    repository._insert.assert_not_called()


@pytest.mark.parametrize("operation", ["verify", "verify_and_rehash"])
def test_invalid_verify_does_not_query(operation):
    repository = MagicMock()
    with pytest.raises(CredentialError):
        getattr(CredentialService(repository), operation)(uuid4(), None)
    repository._verify_and_rehash.assert_not_called()


def test_verify_and_explicit_rehash():
    session = MagicMock()
    old_hash = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1).hash("p")
    session.scalar.return_value = old_hash
    session.execute.return_value.rowcount = 1
    service = CredentialService(UsuarioRepository(session))
    identifier = uuid4()
    assert service.verify(identifier, "p")
    session.execute.assert_not_called()
    assert not service.verify_and_rehash(identifier, "wrong")
    session.execute.assert_not_called()
    assert service.verify_and_rehash(identifier, "p")
    session.execute.assert_called_once()
    session.commit.assert_not_called()
    # Concurrent password changes must not be overwritten.
    session.execute.return_value.rowcount = 0
    assert not service.verify_and_rehash(identifier, "p")


def test_absent_user_and_current_hash_do_not_update():
    session = MagicMock()
    service = CredentialService(UsuarioRepository(session))
    session.scalar.return_value = None
    assert not service.verify(uuid4(), "p")
    session.scalar.return_value = hash_password("p")
    assert service.verify_and_rehash(uuid4(), "p")
    session.execute.assert_not_called()


@pytest.mark.parametrize("operation", ["create", "verify"])
def test_storage_errors_are_sanitized(operation, caplog):
    session = MagicMock()
    session.flush.side_effect = SQLAlchemyError("password_hash secret")
    session.scalar.side_effect = SQLAlchemyError("password_hash secret")
    service = CredentialService(UsuarioRepository(session))
    with pytest.raises(CredentialStorageError) as error:
        if operation == "create":
            service.create("a", "password", "OPERADOR")
        else:
            service.verify(uuid4(), "password")
    assert str(error.value) == "Credential storage unavailable"
    assert "secret" not in caplog.text
    session.commit.assert_not_called()
