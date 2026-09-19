from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.core.rbac import Identidad, Motivo, Permiso, Rol
from app.db.session import build_audit_engine, session_factory
from app.models import Auditoria, Usuario
from app.repositories.auditoria import AuditStorageError, Detalle, Evento, Registro
from app.services.auditoria import AuditoriaService
from app.services.autorizacion import AuthorizationDenied, AutorizacionService

pytestmark = pytest.mark.integration


@pytest.fixture
def audit_database(migration_database):
    engine, config = migration_database
    audit_engine = build_audit_engine(Settings())
    try:
        yield (
            engine,
            config,
            session_factory(engine),
            session_factory(audit_engine),
        )
    finally:
        audit_engine.dispose()


@pytest.mark.parametrize(
    "estado,rol,motivo",
    [
        ("ACTIVO", "INVALID", Motivo.ROL_INVALIDO),
        (None, None, Motivo.IDENTIDAD_INVALIDA),
        ("ACTIVO", Rol.OPERADOR, Motivo.SIN_PERMISO),
        ("BLOQUEADO", Rol.OPERADOR, Motivo.ESTADO_NO_ACTIVO),
        ("INACTIVO", Rol.OPERADOR, Motivo.ESTADO_NO_ACTIVO),
    ],
)
def test_denied_actor_attribution(audit_database, estado, rol, motivo):
    engine, config, business_factory, audit_factory = audit_database
    command.upgrade(config, "head")
    identifier = uuid4()
    known_actor = rol == Rol.OPERADOR
    if known_actor:
        with business_factory.begin() as session:
            session.add(
                Usuario(
                    usuario_id=identifier,
                    email="actor@example.test",
                    password_hash="test-placeholder",
                    rol=rol,
                    estado=estado,
                )
            )
    identity = Identidad(identifier, rol, estado) if rol is not None else None
    # An unpersisted UUID with invalid role must not cause an audit FK failure.
    with pytest.raises(AuthorizationDenied):
        AutorizacionService(AuditoriaService(audit_factory)).autorizar(
            identity, Permiso.USUARIOS_CREAR
        )
    with business_factory() as observer:
        row = observer.scalars(select(Auditoria)).one()
        assert row.usuario_id == (identifier if known_actor else None)
        assert row.accion == Evento.DENEGADA.value
        assert row.detalle["motivo"] == motivo.value


def test_persistence_rollback_and_fk(audit_database):
    engine, config, business_factory, audit_factory = audit_database
    command.upgrade(config, "head")
    assert business_factory.kw["bind"] is not audit_factory.kw["bind"]
    assert business_factory.kw["bind"].pool is not audit_factory.kw["bind"].pool
    with business_factory.begin() as session:
        user = Usuario(
            email="audit@example.test", password_hash="test-placeholder", rol="OPERADOR"
        )
        session.add(user)
        session.flush()
        identifier = user.usuario_id
    identity = Identidad(identifier, Rol.OPERADOR, "ACTIVO")
    audit = AuditoriaService(audit_factory)
    auth = AutorizacionService(audit)
    with Session(engine) as business:
        business.add(
            Usuario(
                email="rollback@example.test", password_hash="unused", rol="AUDITOR"
            )
        )
        business.flush()
        auth.autorizar(identity, Permiso.PEDIDOS_CREAR)
        with pytest.raises(AuthorizationDenied):
            auth.autorizar(identity, Permiso.USUARIOS_CREAR)
        business.rollback()
    with business_factory() as observer:
        rows = observer.scalars(select(Auditoria).order_by(Auditoria.creado_en)).all()
        assert len(rows) == 2
        assert {row.accion for row in rows} == {
            Evento.PERMITIDA.value,
            Evento.DENEGADA.value,
        }
        assert all(
            row.usuario_id == identifier and row.auditoria_id and row.creado_en.tzinfo
            for row in rows
        )
        assert (
            observer.scalar(
                select(Usuario).where(Usuario.email == "rollback@example.test")
            )
            is None
        )
    with pytest.raises(AuthorizationDenied):
        auth.autorizar(None, Permiso.PEDIDOS_CREAR)
    with pytest.raises(AuditStorageError):
        audit.registrar(
            Registro(
                usuario_id=uuid4(),
                evento=Evento.DENEGADA,
                detalle=Detalle(
                    permiso=Permiso.PEDIDOS_CREAR, motivo=Motivo.SIN_PERMISO
                ),
            )
        )
    with business_factory() as observer:
        assert len(observer.scalars(select(Auditoria)).all()) == 3
        with pytest.raises(IntegrityError), observer.begin_nested():
            observer.execute(delete(Usuario).where(Usuario.usuario_id == identifier))
        assert observer.get(Usuario, identifier) is not None
