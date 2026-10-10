"""Validate minimal client lookups against PostgreSQL, including missing rows."""

from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from alembic import command
from app.models.cliente import Cliente
from app.repositories.clientes import ClienteRepository

pytestmark = pytest.mark.integration


def test_existence_does_not_load_profile_and_tracks_deleted_client(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    identifier = uuid4()
    with Session(engine) as session, session.begin():
        session.add(Cliente(cliente_id=identifier, nombre="Cliente sintetico"))
    with Session(engine) as session:
        repository = ClienteRepository(session)
        assert repository.exists(identifier) is True
        assert repository.exists(uuid4()) is False
        assert not session.identity_map
        with Session(engine) as writer, writer.begin():
            writer.execute(delete(Cliente).where(Cliente.cliente_id == identifier))
        assert repository.exists(identifier) is False
