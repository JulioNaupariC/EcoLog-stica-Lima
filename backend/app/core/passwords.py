"""Password operations. Never log inputs or exception details from the backend."""

from argon2 import PasswordHasher, Type, extract_parameters
from argon2.exceptions import (
    HashingError,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, type=Type.ID)


class CredentialError(ValueError):
    """Invalid credential input, without its value."""


class PasswordOperationError(RuntimeError):
    """The password backend could not complete an operation."""


def _validate_password(password: str) -> None:
    if not isinstance(password, str) or not password:
        raise CredentialError("Invalid credential input")


def hash_password(password: str) -> str:
    _validate_password(password)
    try:
        return _hasher.hash(password)
    except (HashingError, UnicodeError):
        raise PasswordOperationError("Password operation unavailable") from None


def verify_password(password: str, password_hash: str) -> bool:
    _validate_password(password)
    if not isinstance(password_hash, str) or not password_hash.startswith("$argon2id$"):
        return False
    try:
        extract_parameters(password_hash)
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, UnicodeError):
        return False
    except VerificationError:
        raise PasswordOperationError("Password operation unavailable") from None


def needs_rehash(password_hash: str) -> bool:
    if not isinstance(password_hash, str) or not password_hash.startswith("$argon2id$"):
        raise CredentialError("Invalid stored credential")
    try:
        return _hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, VerificationError, ValueError):
        raise CredentialError("Invalid stored credential") from None
