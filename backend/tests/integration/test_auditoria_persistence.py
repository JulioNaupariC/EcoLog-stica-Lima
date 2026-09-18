from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.core.rbac import Identidad, Motivo, Permiso, Rol
from app.db.session import session_factory
from app.models import Auditoria, Usuario
from app.repositories.auditoria import AuditStorageError, Detalle, Evento, Registro
from app.services.auditoria import AuditoriaService
from app.services.autorizacion import AuthorizationDenied, AutorizacionService

pytestmark = pytest.mark.integration


def test_persistence_rollback_and_fk(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    with factory.begin() as session:
        user = Usuario(
            email="audit@example.test", password_hash="test-placeholder", rol="OPERADOR"
        )
        session.add(user)
        session.flush()
        identifier = user.usuario_id
    identity = Identidad(identifier, Rol.OPERADOR, "ACTIVO")
    audit = AuditoriaService(factory)
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
    with factory() as observer:
        rows = observer.scalars(select(Auditoria).order_by(Auditoria.creado_en)).all()
        assert len(rows) == 2
        assert {row.accion for row in rows} == {e.value for e in Evento}
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
    with factory() as observer:
        assert len(observer.scalars(select(Auditoria)).all()) == 3
        with pytest.raises(IntegrityError), observer.begin_nested():
            observer.execute(delete(Usuario).where(Usuario.usuario_id == identifier))
        assert observer.get(Usuario, identifier) is not None
