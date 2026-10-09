from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from test_conductor_schemas import payload

from app.core.passwords import PasswordOperationError
from app.models.conductor import Conductor
from app.models.usuario import Usuario
from app.repositories.conductores import ConductorRepository
from app.schemas.conductor import ConductorCreate, ConductorUpdate
from app.services.conductores import (
    ConductorConflict,
    ConductorInvalid,
    ConductorNotFound,
    ConductorService,
    ConductorUnavailable,
    _response,
    _translate_integrity,
)


def setup_service():
    session = MagicMock()
    factory = MagicMock()
    factory.begin.return_value.__enter__.return_value = session
    factory.return_value.__enter__.return_value = session
    return ConductorService(factory), session, factory


def driver():
    data = payload()
    data.pop("email")
    data.pop("password")
    parsed = ConductorCreate.model_validate(payload())
    data = parsed.model_dump(exclude={"email", "password"})
    return Conductor(
        conductor_id=uuid4(),
        usuario_id=uuid4(),
        estado="ACTIVO",
        **data,
    )


def account(owner):
    return Usuario(usuario_id=owner, rol="CONDUCTOR", estado="ACTIVO")


def test_registration_uses_hash_adapter_and_distinct_new_account():
    service, session, _ = setup_service()

    def flush():
        for call in session.add.call_args_list:
            obj = call.args[0]
            if isinstance(obj, Usuario) and obj.usuario_id is None:
                obj.usuario_id = uuid4()
            elif isinstance(obj, Conductor) and obj.conductor_id is None:
                obj.conductor_id = uuid4()

    session.flush.side_effect = flush
    with patch(
        "app.services.conductores.hash_password", return_value="encoded"
    ) as hasher:
        result = service.create(ConductorCreate.model_validate(payload()))
    hasher.assert_called_once_with(payload()["password"])
    user = session.add.call_args_list[0].args[0]
    assert user.rol == "CONDUCTOR" and user.password_hash == "encoded"
    assert result.usuario_id == user.usuario_id
    assert not {"dni", "password"} & result.model_dump().keys()


@pytest.mark.parametrize(
    "constraint,expected",
    [
        ("uq_conductor_dni", ConductorConflict),
        ("uq_usuario_email", ConductorConflict),
        ("uq_conductor_usuario_id", ConductorConflict),
        ("other_constraint", ConductorUnavailable),
    ],
)
def test_integrity_errors_are_translated(constraint, expected):
    original = Exception("private SQL")
    original.diag = SimpleNamespace(constraint_name=constraint)
    with pytest.raises(expected, match="registrado|disponible"):
        _translate_integrity(IntegrityError("private statement", {}, original))


@pytest.mark.parametrize("operation", ["create", "get", "list_page", "update"])
def test_storage_failures_are_sanitized(operation):
    service, session, _ = setup_service()
    session.flush.side_effect = SQLAlchemyError("private SQL")
    session.scalar.side_effect = SQLAlchemyError("private SQL")
    args = {
        "create": (ConductorCreate.model_validate(payload()),),
        "get": (uuid4(),),
        "list_page": (1, 20),
        "update": (uuid4(), ConductorUpdate(nombre="Nuevo")),
    }
    with pytest.raises(ConductorUnavailable) as error:
        getattr(service, operation)(*args[operation])
    assert "private" not in str(error.value)


def test_password_backend_failure_is_sanitized():
    service, _, _ = setup_service()
    with patch(
        "app.services.conductores.hash_password", side_effect=PasswordOperationError()
    ):
        with pytest.raises(ConductorUnavailable):
            service.create(ConductorCreate.model_validate(payload()))


def test_read_page_and_update_validate_resulting_profile():
    service, session, _ = setup_service()
    row = driver()
    session.scalar.return_value = row
    session.get.return_value = account(row.usuario_id)
    assert service.get(row.conductor_id).habilitado_asignacion
    session.scalar.return_value = 1
    session.scalars.return_value = [row]
    result = service.list_page(1, 20)
    assert result.total == 1
    assert "dni" not in result.items[0].model_dump()
    session.scalar.return_value = row
    assert (
        service.update(row.conductor_id, ConductorUpdate(nombre="Nuevo")).nombre
        == "Nuevo"
    )
    original = row.disponible_hasta
    with pytest.raises(ConductorInvalid):
        service.update(
            row.conductor_id,
            ConductorUpdate(
                disponible_desde=original,
                disponible_hasta=original - timedelta(hours=1),
            ),
        )
    assert row.disponible_hasta == original
    assert (
        service.update(
            row.conductor_id,
            ConductorUpdate(
                disponible_desde=None,
                disponible_hasta=None,
            ),
        ).habilitado_asignacion
        is False
    )


@pytest.mark.parametrize("operation", ["get", "update"])
def test_not_found(operation):
    service, session, _ = setup_service()
    session.scalar.return_value = None
    args = (
        (uuid4(),) if operation == "get" else (uuid4(), ConductorUpdate(nombre="Nuevo"))
    )
    with pytest.raises(ConductorNotFound):
        getattr(service, operation)(*args)


@pytest.mark.parametrize(
    "case",
    [
        "expired",
        "no_interval",
        "past",
        "inactive_driver",
        "inactive_user",
        "wrong_role",
        "no_user",
    ],
)
def test_nonassignable_profiles(case):
    row = driver()
    user = account(row.usuario_id)
    if case == "expired":
        row.licencia_vigente_hasta = date(2000, 1, 1)
    elif case == "no_interval":
        row.disponible_desde = row.disponible_hasta = None
    elif case == "past":
        row.disponible_hasta = datetime.now(timezone.utc) - timedelta(hours=1)
    elif case == "inactive_driver":
        row.estado = "INACTIVO"
    elif case == "inactive_user":
        user.estado = "INACTIVO"
    elif case == "wrong_role":
        user.rol = "OPERADOR"
    else:
        user = None
    assert _response(row, user).habilitado_asignacion is False


def test_repository_orders_paginates_and_locks():
    session = MagicMock()
    repository = ConductorRepository(session)
    repository.get(uuid4(), lock=True)
    assert "FOR UPDATE" in str(session.scalar.call_args.args[0])
    session.scalar.return_value = 0
    session.scalars.return_value = []
    assert repository.list_page(2, 10) == ([], 0)
    statement = str(session.scalars.call_args.args[0])
    assert "ORDER BY conductor.conductor_id" in statement and "OFFSET" in statement


def test_license_is_valid_through_its_final_local_day():
    from app.services.conductores import LIMA

    row = driver()
    user = account(row.usuario_id)
    row.licencia_vigente_hasta = date(2026, 10, 9)
    row.disponible_desde = datetime(2026, 10, 9, 8, tzinfo=LIMA)
    row.disponible_hasta = datetime(2026, 10, 10, 12, tzinfo=LIMA)
    with patch("app.services.conductores.datetime") as clock:
        clock.now.return_value = datetime(2026, 10, 9, 23, 59, tzinfo=LIMA)
        assert _response(row, user).habilitado_asignacion is True
        clock.now.return_value = datetime(2026, 10, 10, 0, 0, tzinfo=LIMA)
        assert _response(row, user).habilitado_asignacion is False
