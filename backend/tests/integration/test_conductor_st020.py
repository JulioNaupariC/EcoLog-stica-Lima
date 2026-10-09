"""Conductor PostgreSQL integration checks on a disposable database only."""

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.models import Conductor, Usuario

pytestmark = pytest.mark.integration


def user(email):
    return Usuario(
        email=email,
        password_hash="integration-fixture-hash",
        rol="CONDUCTOR",
    )


def data(account, **changes):
    values = {
        "usuario_id": account.usuario_id,
        "nombre": "Prueba",
        "dni": "01234567",
        "licencia_numero": "L0001",
        "licencia_vigente_hasta": date(2025, 1, 1),
        "experiencia_anios": 0,
        "telefono": "+51987654321",
        "punto_partida": "Base",
        "disponible_desde": None,
        "disponible_hasta": None,
    }
    values.update(changes)
    return Conductor(**values)


def test_conductor_upgrade_downgrade_and_existing_tables(migration_database):
    engine, config = migration_database
    command.upgrade(config, "0006_create_cliente_pedido")
    with engine.connect() as connection:
        assert not inspect(connection).has_table("conductor")

    command.upgrade(config, "head")
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert inspector.has_table("conductor")
        assert all(
            inspector.has_table(name)
            for name in (
                "usuario",
                "vehiculo",
                "pedido",
                "cliente",
                "auditoria",
                "sesion",
            )
        )
        assert "uq_conductor_dni" in {
            item["name"] for item in inspector.get_unique_constraints("conductor")
        }

    command.downgrade(config, "0006_create_cliente_pedido")
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert not inspector.has_table("conductor")
        assert inspector.has_table("pedido")
    command.upgrade(config, "head")
    command.check(config)


def test_conductor_persistence_and_rejections(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    with Session(engine) as session:
        account_a = user("driver-a@sample.invalid")
        account_b = user("driver-b@sample.invalid")
        session.add_all([account_a, account_b])
        session.flush()

        valid = data(account_a)
        session.add(valid)
        session.commit()
        session.refresh(valid)
        assert valid.conductor_id and valid.estado == "ACTIVO"
        assert valid.dni == "01234567"

        invalid = (
            {"usuario_id": account_a.usuario_id, "dni": "22222222"},
            {"usuario_id": account_b.usuario_id, "dni": "01234567"},
            {"usuario_id": account_b.usuario_id, "dni": "ABC"},
            {
                "usuario_id": account_b.usuario_id,
                "dni": "22222222",
                "experiencia_anios": -1,
            },
            {
                "usuario_id": account_b.usuario_id,
                "dni": "22222222",
                "disponible_desde": datetime.now(timezone.utc),
            },
            {
                "usuario_id": account_b.usuario_id,
                "dni": "22222222",
                "estado": "BORRADO",
            },
        )
        for change in invalid:
            session.add(data(account_b, **change))
            with pytest.raises(IntegrityError):
                session.flush()
            session.rollback()

        account_b = session.query(Usuario).filter_by(
            email="driver-b@sample.invalid"
        ).one()
        start = datetime(2026, 10, 9, 8, tzinfo=timezone.utc)
        good = data(
            account_b,
            dni="87654321",
            disponible_desde=start,
            disponible_hasta=start + timedelta(hours=9),
        )
        session.add(good)
        session.commit()
        assert good.conductor_id is not None
        # RN-005 constrains driving time, not availability interval length.
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.add(
                    data(
                        account_b,
                        dni="33333333",
                        disponible_desde=start,
                        disponible_hasta=start,
                    )
                )
                session.flush()


def test_fk_rejects_unknown_user(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    with Session(engine) as session:
        session.add(
            Conductor(
                usuario_id=uuid4(),
                nombre="A",
                dni="11223344",
                licencia_numero="LIC",
                licencia_vigente_hasta=date(2026, 1, 1),
                experiencia_anios=1,
                telefono="+51987654321",
                punto_partida="Base",
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
