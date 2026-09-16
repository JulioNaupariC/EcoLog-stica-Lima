import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.core.passwords import verify_password
from app.models import Usuario
from app.repositories.usuarios import UsuarioRepository
from app.services.credenciales import CredentialService

pytestmark = pytest.mark.integration


def test_persistence_and_constraints(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    try:
        with Session(engine) as session:
            service = CredentialService(UsuarioRepository(session))
            user = service.create("test@example.test", " contraseña ", "OPERADOR")
            stored = session.scalar(select(Usuario.password_hash))
            assert stored != " contraseña "
            assert verify_password(" contraseña ", stored)
            assert user.estado == "ACTIVO"
            # No implicit commit: a separate transaction cannot see the row.
            with Session(engine) as observer:
                assert observer.scalar(select(Usuario.usuario_id)) is None
            for overrides in (
                {},
                {"email": "other@example.test", "rol": "INVALID"},
                {"email": "other@example.test", "estado": "INVALID"},
            ):
                with pytest.raises(IntegrityError), session.begin_nested():
                    fields = dict(
                        email="test@example.test",
                        password_hash=stored,
                        rol="OPERADOR",
                        estado="ACTIVO",
                    )
                    fields.update(overrides)
                    session.add(Usuario(**fields))
                    session.flush()
            session.rollback()
    finally:
        command.downgrade(config, "base")
