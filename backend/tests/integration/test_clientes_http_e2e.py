"""ECL-53 / D-01: búsqueda real de clientes por HTTP sobre PostgreSQL."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from alembic import command
from app.core.config import Settings
from app.db.session import session_factory
from app.main import create_app
from app.models import Auditoria, Cliente
from app.repositories.usuarios import UsuarioRepository
from app.services.credenciales import CredentialService

pytestmark = pytest.mark.integration

PASSWORD = "synthetic-test-password"
NAMES = (
    "Bodega Ficticia Norte",
    "Bodega Ficticia Sur",
    "Farmacia Ejemplo Centro",
    "Comercial 50% Demo",
    "Comercial 500 Demo",
)


@pytest.fixture
def clientes_app(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    with factory.begin() as session:
        credentials = CredentialService(UsuarioRepository(session))
        for role in ("OPERADOR", "CONDUCTOR"):
            credentials.create(f"{role.lower()}@example.test", PASSWORD, role)
        rows = [Cliente(nombre=name) for name in NAMES]
        session.add_all(rows)
        session.flush()
        ids = {row.nombre: row.cliente_id for row in rows}
    app = create_app(
        Settings(app_env="test", database_url=config.attributes["database_url"])
    )
    try:
        yield app, ids
    finally:
        with factory.begin() as session:
            session.execute(delete(Auditoria))


def login(client, role):
    response = client.post(
        "/login", json={"email": f"{role.lower()}@example.test", "password": PASSWORD}
    )
    assert response.status_code == 200


def names(response):
    return [item["nombre"] for item in response.json()["items"]]


def test_ruta_dorada_operador_encuentra_cliente_por_fragmento(clientes_app):
    """Ruta dorada: «bodega» devuelve ambas bodegas ordenadas, sin otros datos."""
    app, _ = clientes_app
    with TestClient(app) as client:
        login(client, "OPERADOR")
        response = client.get("/clientes", params={"buscar": "  bodega "})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert names(response) == ["Bodega Ficticia Norte", "Bodega Ficticia Sur"]
    assert response.json()["total"] == 2
    assert set(response.json()["items"][0]) == {"cliente_id", "nombre"}


def test_ruta_feliz_paginacion_y_busqueda_por_identificador(clientes_app):
    """Ruta feliz: paginación estable y coincidencia exacta por UUID."""
    app, ids = clientes_app
    with TestClient(app) as client:
        login(client, "OPERADOR")
        first = client.get("/clientes", params={"page": 1, "page_size": 2})
        second = client.get("/clientes", params={"page": 2, "page_size": 2})
        by_id = client.get(
            "/clientes", params={"buscar": str(ids["Farmacia Ejemplo Centro"])}
        )
    assert first.json()["total"] == len(NAMES)
    assert not set(names(first)) & set(names(second))
    assert names(by_id) == ["Farmacia Ejemplo Centro"]


def test_ruta_infeliz_conductor_y_anonimo_no_listan_clientes(clientes_app):
    """Ruta infeliz: sin sesión 401; conductor sin alcance general 403."""
    app, _ = clientes_app
    with TestClient(app) as client:
        assert client.get("/clientes").status_code == 401
        login(client, "CONDUCTOR")
        denied = client.get("/clientes")
    assert denied.status_code == 403
    assert "Bodega" not in denied.text


def test_ruta_de_borde_comodines_literales_y_sin_coincidencias(clientes_app):
    """Ruta de borde: «%» se busca literalmente y un término ausente da 0."""
    app, _ = clientes_app
    with TestClient(app) as client:
        login(client, "OPERADOR")
        literal = client.get("/clientes", params={"buscar": "50%"})
        underscore = client.get("/clientes", params={"buscar": "_"})
        none = client.get("/clientes", params={"buscar": "inexistente"})
        beyond = client.get("/clientes", params={"page": 99})
    assert names(literal) == ["Comercial 50% Demo"]
    assert underscore.json()["total"] == 0
    assert none.json() == {"items": [], "page": 1, "page_size": 20, "total": 0}
    assert beyond.json()["items"] == [] and beyond.json()["total"] == len(NAMES)
