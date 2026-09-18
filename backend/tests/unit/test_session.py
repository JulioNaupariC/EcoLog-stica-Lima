from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.db.session import (
    build_audit_engine,
    build_engine,
    get_session,
    session_factory,
)


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


def test_audit_factory_has_independent_engine_and_pool():
    settings = Settings(database_url="postgresql+psycopg://localhost/db")
    business_engine = build_engine(settings)
    audit_engine = build_audit_engine(settings)
    try:
        business_factory = session_factory(business_engine)
        audit_factory = session_factory(audit_engine)
        assert business_factory.kw["bind"] is business_engine
        assert audit_factory.kw["bind"] is audit_engine
        assert audit_engine is not business_engine
        assert audit_engine.pool is not business_engine.pool
        assert audit_engine.url == business_engine.url
    finally:
        audit_engine.dispose()
        business_engine.dispose()


def test_session_rollback_and_close_on_error():
    factory = MagicMock()
    session = factory.return_value.__enter__.return_value
    iterator = get_session(factory)
    assert next(iterator) is session
    with pytest.raises(RuntimeError):
        iterator.throw(RuntimeError("operation failed"))
    session.rollback.assert_called_once()
    factory.return_value.__exit__.assert_called_once()
