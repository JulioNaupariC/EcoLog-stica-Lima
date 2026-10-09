"""PostgreSQL/PostGIS integration checks: disposable TEST_DATABASE_URL only."""

from datetime import date, datetime, timedelta, timezone
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from alembic import command
from app.models import Conductor, Usuario

pytestmark = pytest.mark.integration


def user(email):
    return Usuario(email=email, password_hash="integration-fixture-hash", rol="CONDUCTOR")


def data(account, **changes):
    base = dict(usuario_id=account.usuario_id, nombre="Prueba", dni="01234567", licencia_numero="L0001", licencia_vigente_hasta=date(2025, 1, 1), experiencia_anios=0, telefono="+51987654321", punto_partida="Base", disponible_desde=None, disponible_hasta=None)
    base.update(changes)
    return Conductor(**base)


def test_conductor_upgrade_downgrade_and_existing_tables(migration_database):
    engine, config = migration_database
    command.upgrade(config, "0006_create_cliente_pedido")
    with engine.connect() as conn:
        assert not inspect(conn).has_table("conductor")
    command.upgrade(config, "head")
    with engine.connect() as conn:
        insp = inspect(conn)
        assert insp.has_table("conductor")
        assert {t for t in ("usuario", "vehiculo", "pedido", "cliente", "auditoria", "sesion") if insp.has_table(t)} == {"usuario", "vehiculo", "pedido", "cliente", "auditoria", "sesion"}
        assert "uq_conductor_dni" in {c["name"] for c in insp.get_unique_constraints("conductor")}
    command.downgrade(config, "0006_create_cliente_pedido")
    with engine.connect() as conn:
        assert not inspect(conn).has_table("conductor")
        assert inspect(conn).has_table("pedido")
    command.upgrade(config, "head")
    command.check(config)


def test_conductor_persistence_and_rejections(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    with Session(engine) as session:
        a, b = user("driver-a@sample.invalid"), user("driver-b@sample.invalid")
        session.add_all([a, b]); session.flush()
        valid = data(a)
        session.add(valid); session.commit(); session.refresh(valid)
        assert valid.conductor_id and valid.estado == "ACTIVO"
        assert valid.dni == "01234567"  # leading zero preserved
        for change in (dict(usuario_id=a.usuario_id, dni="22222222"), dict(usuario_id=b.usuario_id, dni="01234567"), dict(usuario_id=b.usuario_id, dni="ABC"), dict(usuario_id=b.usuario_id, dni="22222222", experiencia_anios=-1), dict(usuario_id=b.usuario_id, dni="22222222", disponible_desde=datetime.now(timezone.utc)), dict(usuario_id=b.usuario_id, dni="22222222", estado="BORRADO")):
            session.add(data(b, **change))
            with pytest.raises(IntegrityError):
                session.flush()
            session.rollback()
            # A rollback reverts uncommitted records; fixtures and first conductor were committed.
        b = session.query(Usuario).filter_by(email="driver-b@sample.invalid").one()
        begin = datetime(2026, 10, 9, 8, tzinfo=timezone.utc)
        good = data(b, dni="87654321", disponible_desde=begin, disponible_hasta=begin + timedelta(hours=9))
        session.add(good); session.commit()
        assert good.conductor_id is not None  # availability >8h is allowed; RN-005 is about driving.
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.add(data(b, dni="33333333", disponible_desde=begin, disponible_hasta=begin))
                session.flush()


def test_fk_rejects_unknown_user(migration_database):
    from uuid import uuid4
    engine, config = migration_database
    command.upgrade(config, "head")
    with Session(engine) as session:
        session.add(Conductor(usuario_id=uuid4(), nombre="A", dni="11223344", licencia_numero="LIC", licencia_vigente_hasta=date(2026,1,1), experiencia_anios=1, telefono="+51987654321", punto_partida="Base"))
        with pytest.raises(IntegrityError):
            session.flush()
