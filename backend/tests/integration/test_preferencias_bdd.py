"""ECL-54: contrast P1-P6 against real HTTP and PostgreSQL persistence."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.db.session import session_factory
from app.main import create_app
from app.models import Auditoria, Cliente
from app.repositories.usuarios import UsuarioRepository
from app.services.credenciales import CredentialService

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("role", ["ADMINISTRADOR", "OPERADOR"])
def test_bdd_preferences_matrix(migration_database, role):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    other = {
        "horario_preferido": "Tarde (preferido)",
        "referencia": "Recepcion principal",
        "restriccion_acceso": "Avisar al llegar",
    }
    with factory.begin() as session:
        CredentialService(UsuarioRepository(session)).create(
            "bdd-ecl54@example.test", "synthetic-test-password", role
        )
        first = Cliente(nombre="Cliente A sintetico")
        second = Cliente(nombre="Cliente B sintetico", **other)
        session.add_all([first, second])
        session.flush()
        first_id, second_id = first.cliente_id, second.cliente_id
    app = create_app(
        Settings(app_env="test", database_url=config.attributes["database_url"])
    )
    first_url = f"/clientes/{first_id}/preferencias"
    second_url = f"/clientes/{second_id}/preferencias"
    try:
        with TestClient(app) as client:
            assert (
                client.post(
                    "/login",
                    json={
                        "email": "bdd-ecl54@example.test",
                        "password": "synthetic-test-password",
                    },
                ).status_code
                == 200
            )
            initial = client.get(first_url)
            assert initial.status_code == 200
            assert initial.headers["cache-control"] == "no-store"
            assert initial.json() == {
                "cliente_id": str(first_id),
                "horario_preferido": None,
                "referencia": None,
                "restriccion_acceso": None,
            }
            valid = {
                "horario_preferido": "  Manana (preferido)  ",
                "referencia": "Puerta junto al parque",
                "restriccion_acceso": "Ingreso por puerta lateral",
            }
            saved = client.patch(first_url, json=valid)
            assert saved.status_code == 200
            assert saved.json() == {"cliente_id": str(first_id), **valid}
            updated = {**valid, "referencia": "Entrada norte"}
            assert client.patch(first_url, json=updated).status_code == 200
            assert client.get(first_url).json() == {
                "cliente_id": str(first_id),
                **updated,
            }
            # P3: inclusive boundary and rejected boundary+1 for every field.
            for field, limit in (
                ("horario_preferido", 120),
                ("referencia", 255),
                ("restriccion_acceso", 255),
            ):
                boundary = client.patch(first_url, json={field: "x" * limit})
                assert boundary.status_code == 200
                snapshot = boundary.json()
                for value in (
                    "x" * (limit + 1),
                    "",
                    "   ",
                    123,
                    True,
                    [],
                    {},
                    "a\x00b",
                ):
                    rejected = client.patch(first_url, json={field: value})
                    assert rejected.status_code == 422
                    assert any(
                        item["loc"][-1] == field for item in rejected.json()["detail"]
                    )
                    assert all(
                        "input" not in item for item in rejected.json()["detail"]
                    )
                    assert client.get(first_url).json() == snapshot
                assert client.patch(first_url, json=updated).status_code == 200
            # P4a / P4b: omitted values kept, explicit null only clears target.
            partial = client.patch(first_url, json={"referencia": "Entrada sur"})
            assert partial.json() == {
                "cliente_id": str(first_id),
                **updated,
                "referencia": "Entrada sur",
            }
            cleared = client.patch(first_url, json={"restriccion_acceso": None})
            assert cleared.status_code == 200
            assert cleared.json() == {**partial.json(), "restriccion_acceso": None}
            for bad in ({}, {"cliente_id": str(second_id)}, {"unknown": "value"}):
                assert client.patch(first_url, json=bad).status_code == 422
                assert client.get(first_url).json() == cleared.json()
            # P5 / P6: no new association and no change to other populated client.
            missing = f"/clientes/{uuid4()}/preferencias"
            assert client.get(missing).status_code == 404
            assert client.patch(missing, json=valid).status_code == 404
            assert client.get(second_url).json() == {
                "cliente_id": str(second_id),
                **other,
            }
            with Session(engine) as session:
                assert session.scalar(select(func.count()).select_from(Cliente)) == 2
                assert session.get(Cliente, first_id).nombre == "Cliente A sintetico"
                assert session.get(Cliente, second_id).referencia == other["referencia"]
                assert session.get(Cliente, first_id).restriccion_acceso is None
    finally:
        with factory.begin() as session:
            session.execute(delete(Auditoria))
