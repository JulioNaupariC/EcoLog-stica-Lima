import re

import pytest

from app.core.session_tokens import generate_session_token, hash_session_token


def test_tokens_are_random_and_only_digest_is_storage_sized():
    first = generate_session_token()
    second = generate_session_token()
    assert first != second
    assert len(first) >= 43
    digest = hash_session_token(first)
    assert digest != first
    assert re.fullmatch(r"[0-9a-f]{64}", digest)


@pytest.mark.parametrize("token", [None, "", 123, b"token"])
def test_invalid_tokens_are_rejected(token):
    with pytest.raises(ValueError, match="^Invalid session token$"):
        hash_session_token(token)
