"""Opaque session tokens. Only their digest crosses the persistence boundary."""

import hashlib
import secrets


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    if not isinstance(token, str) or not token:
        raise ValueError("Invalid session token")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
