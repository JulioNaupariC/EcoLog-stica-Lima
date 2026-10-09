"""Real HTTP authorization, persistence and preference use in order preparation."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.db.session import session_factory
from app.main import create_app
from app.models import Auditoria, Cliente, Pedido
from app.repositories.preferencias import PreferenciasRepository
from app.repositories.usuarios import UsuarioRepository
from app.services.credenciales import CredentialService

pytestmark = pytest.mark.integration


def seed(engine, config, role):
    command.upgrade(config, "head")
    factory = session_factory(engine)
    with factory.begin() as session:
        CredentialService(UsuarioRepository(session)).create(
            "preferences-user@example.test", "synthetic-test-password", role
        )
        first, second = (
            Cliente(nombre="Cliente A sintético"),
            Cliente(nombre="Cliente B sintético"),
        )
        session.add_all([first, second])
        session.flush()
        ids = first.cliente_id, second.cliente_id
    app = create_app(
        Settings(app_env="test", database_url=config.attributes["database_url"])
    )
    return app, factory, ids


def clear_audit(factory):
    # Only the explicitly empty disposable migration test database is used.
    with factory.begin() as session:
        session.execute(delete(Auditoria))


def login(client):
    assert (
        client.post(
            "/login",
            json={
                "email": "preferences-user@example.test",
                "password": "synthetic-test-password",
            },
        ).status_code
        == 200
    )


@pytest.mark.parametrize("role", ["ADMINISTRADOR", "OPERADOR"])
def test_preferences_association_validation_and_order_preparation(
    migration_database, role
):
    engine, config = migration_database
    app, factory, (first, second) = seed(engine, config, role)
    url = f"/clientes/{first}/preferencias"
    try:
        with TestClient(app) as client:
            login(client)
            assert client.get(url).json()["referencia"] is None
            prefs = {
                "horario_preferido": "  Mañana (preferido)  ",
                "referencia": "Puerta del parque",
                "restriccion_acceso": "Ingreso lateral",
            }
            saved = client.patch(url, json=prefs)
            assert saved.status_code == 200
            assert saved.json() == {"cliente_id": str(first), **prefs}
            assert (
                client.get(f"/clientes/{second}/preferencias").json()["referencia"]
                is None
            )
            for bad in (
                {"referencia": ""},
                {"referencia": "  "},
                {"referencia": "x" * 256},
                {"referencia": "Otra", "horario_preferido": "x" * 121},
                {"referencia": "Otra", "cliente_id": str(second)},
                {"referencia": "a\x00b"},
            ):
                assert client.patch(url, json=bad).status_code == 422
                assert client.get(url).json() == saved.json()
            # The caller explicitly selects the retrieved client reference.
            order = client.post(
                "/pedidos",
                json={
                    "cliente_id": str(first),
                    "direccion": "Av. de prueba 123",
                    "referencia": client.get(url).json()["referencia"],
                    "peso_kg": "2.00",
                    "volumen_m3": "0.050",
                    "ventana_inicio": "2026-10-10T09:00:00-05:00",
                    "ventana_fin": "2026-10-10T11:00:00-05:00",
                    "prioridad": "ESTANDAR",
                    "tipo_producto": "PRUEBA",
                },
            )
            assert order.status_code == 201
            assert order.json()["referencia"] == prefs["referencia"]
            assert client.get(url).json() == saved.json()
            partial = client.patch(url, json={"restriccion_acceso": None})
            assert partial.status_code == 200
            assert partial.json()["restriccion_acceso"] is None
            assert partial.json()["horario_preferido"] == prefs["horario_preferido"]
            assert partial.json()["referencia"] == prefs["referencia"]
            assert (
                client.patch(url, json={"referencia": "Entrada nueva"}).status_code
                == 200
            )
            with Session(engine) as session:
                row = session.get(Cliente, first)
                assert (
                    row.referencia == "Entrada nueva"
                    and row.nombre == "Cliente A sintético"
                )
                assert session.get(Cliente, second).referencia is None
                assert (
                    session.get(Pedido, order.json()["pedido_id"]).referencia
                    == "Puerta del parque"
                )
            missing = f"/clientes/{uuid4()}/preferencias"
            assert client.get(missing).status_code == 404
            assert (
                client.patch(missing, json={"referencia": "Entrada"}).status_code == 404
            )
    finally:
        clear_audit(factory)


@pytest.mark.parametrize("role", ["CONDUCTOR", "ANALISTA", "AUDITOR"])
def test_disallowed_roles_and_unauthenticated_cannot_read_or_change(
    migration_database, role
):
    engine, config = migration_database
    app, factory, (first, _) = seed(engine, config, role)
    url = f"/clientes/{first}/preferencias"
    try:
        with TestClient(app) as client:
            assert client.get(url).status_code == 401
            assert client.patch(url, json={"referencia": "Entrada"}).status_code == 401
            login(client)
            assert client.get(url).status_code == 403
            assert client.patch(url, json={"referencia": "Entrada"}).status_code == 403
        with Session(engine) as session:
            assert session.get(Cliente, first).referencia is None
    finally:
        clear_audit(factory)


def test_failed_transaction_rolls_back_preferences(migration_database, monkeypatch):
    engine, config = migration_database
    app, factory, (first, _) = seed(engine, config, "OPERADOR")
    url = f"/clientes/{first}/preferencias"
    original = PreferenciasRepository.flush

    def failing_flush(repository):
        original(repository)
        raise SQLAlchemyError("private storage details")

    try:
        with TestClient(app) as client:
            login(client)
            monkeypatch.setattr(PreferenciasRepository, "flush", failing_flush)
            response = client.patch(url, json={"referencia": "No debe persistir"})
            assert response.status_code == 503 and "private" not in response.text
            assert client.get(url).json()["referencia"] is None
        with Session(engine) as session:
            assert session.get(Cliente, first).referencia is None
    finally:
        clear_audit(factory)
