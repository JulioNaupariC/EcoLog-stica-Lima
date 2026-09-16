from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.db.session import build_engine, get_session, session_factory


def test_missing_configuration():
    with pytest.raises(ValueError, match="DATABASE_URL"):
        build_engine(Settings())


def test_engine_and_session_without_network():
    engine = build_engine(Settings(database_url="postgresql+psycopg://localhost/db"))
    try:
        assert engine.dialect.driver == "psycopg"
        factory = session_factory(engine)
        iterator = get_session(factory)
        session = next(iterator)
        assert session.bind is engine
        iterator.close()
    finally:
        engine.dispose()


def test_session_rollback_and_close_on_error():
    factory = MagicMock()
    session = factory.return_value.__enter__.return_value
    iterator = get_session(factory)
    assert next(iterator) is session
    with pytest.raises(RuntimeError):
        iterator.throw(RuntimeError("operation failed"))
    session.rollback.assert_called_once()
    factory.return_value.__exit__.assert_called_once()
