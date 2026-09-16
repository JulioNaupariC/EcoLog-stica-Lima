from unittest.mock import Mock

import pytest
from argon2 import PasswordHasher, Type
from argon2.exceptions import HashingError, VerificationError

from app.core.passwords import (
    CredentialError,
    PasswordOperationError,
    hash_password,
    needs_rehash,
    verify_password,
)


def test_hash_verify_salt_and_profile():
    first = hash_password("contraseña de prueba")
    second = hash_password("contraseña de prueba")
    assert first != second
    assert first.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert verify_password("contraseña de prueba", first)
    assert verify_password("contraseña de prueba", second)
    assert not verify_password("incorrecta", first)
    assert not needs_rehash(first)
    assert len(first) <= 255


@pytest.mark.parametrize("value", [None, 123, b"password", [], {}, ""])
def test_invalid_password_rejected_without_echo(value):
    for operation in (hash_password, lambda v: verify_password(v, "invalid")):
        with pytest.raises(CredentialError, match="^Invalid credential input$"):
            operation(value)


@pytest.mark.parametrize("password", [" ", " á漢字🙂 ", "a" * 2048])
def test_preserves_spaces_unicode_and_long_passwords(password):
    stored = hash_password(password)
    assert verify_password(password, stored)
    assert not verify_password(password + " ", stored)


@pytest.mark.parametrize("stored", [None, 123, "", "clear text", "$argon2id$broken"])
def test_invalid_hash_fails_safely(stored):
    assert not verify_password("password", stored)
    with pytest.raises(CredentialError, match="^Invalid stored credential$"):
        needs_rehash(stored)


def test_old_parameters_need_rehash():
    stored = PasswordHasher(
        time_cost=2, memory_cost=19456, parallelism=1, type=Type.ID
    ).hash("password")
    assert verify_password("password", stored)
    assert needs_rehash(stored)


def test_hashing_failure_does_not_expose_secrets(monkeypatch, caplog):
    monkeypatch.setattr(
        "app.core.passwords._hasher",
        Mock(hash=Mock(side_effect=HashingError("password secret"))),
    )
    with pytest.raises(PasswordOperationError) as error:
        hash_password("password secret")
    assert "secret" not in str(error.value)
    assert "secret" not in caplog.text


def test_verification_backend_failure_is_sanitized(monkeypatch, caplog):
    stored = hash_password("password secret")
    monkeypatch.setattr(
        "app.core.passwords._hasher",
        Mock(verify=Mock(side_effect=VerificationError("password secret"))),
    )
    with pytest.raises(PasswordOperationError) as error:
        verify_password("password secret", stored)
    assert "secret" not in str(error.value)
    assert stored not in caplog.text
    assert "secret" not in caplog.text
