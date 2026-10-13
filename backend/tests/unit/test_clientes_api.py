"""ECL-53 / D-01: búsqueda paginada de clientes para los selectores."""

from contextlib import contextmanager
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.clientes import get_cliente_service
from app.api.dependencies import get_authenticated_session
from app.core.config import Settings
from app.core.rbac import Identidad, Rol
from app.main import create_app
from app.repositories.clientes import ClienteRepository, ClienteStorageError
from app.schemas.cliente import ClienteListItem, ClientePage
from app.services.autenticacion import AuthenticatedSession
from app.services.autorizacion import AutorizacionService
from app.services.clientes import (
    ClienteSearchInvalid,
    ClienteService,
    ClientesUnavailable,
    normalize_term,
)


@contextmanager
def client_for(role=Rol.OPERADOR):
    app = create_app(Settings(database_url=None))
    service = Mock()
    identity = Identidad(uuid4(), role, "ACTIVO")
    app.dependency_overrides[get_authenticated_session] = lambda: AuthenticatedSession(
        uuid4(), identity
    )
    app.dependency_overrides[get_cliente_service] = lambda: service
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(Mock())
        yield client, service


def page_with(*names):
    return ClientePage(
        items=[ClienteListItem(cliente_id=uuid4(), nombre=name) for name in names],
        page=1,
        page_size=20,
        total=len(names),
    )


def test_ruta_dorada_operador_busca_por_nombre_con_proyeccion_minima():
    """Ruta dorada: el operador obtiene solo identificador y nombre."""
    with client_for() as (client, service):
        service.search.return_value = page_with("Bodega Ficticia Norte")
        result = client.get("/clientes", params={"buscar": "bodega"})
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    assert set(result.json()["items"][0]) == {"cliente_id", "nombre"}
    service.search.assert_called_once_with("bodega", 1, 20)


@pytest.mark.parametrize("role", list(Rol))
def test_ruta_feliz_y_permisos_por_rol(role):
    """Ruta feliz para ADMINISTRADOR/OPERADOR; el resto recibe 403 sin consulta."""
    with client_for(role) as (client, service):
        service.search.return_value = page_with()
        result = client.get("/clientes")
    if role in {Rol.ADMINISTRADOR, Rol.OPERADOR}:
        assert result.status_code == 200
        service.search.assert_called_once_with(None, 1, 20)
    else:
        assert result.status_code == 403
        service.search.assert_not_called()


@pytest.mark.parametrize(
    "params",
    [
        {"page": "0"},
        {"page_size": "0"},
        {"page_size": "51"},
        {"buscar": "x" * 161},
        {"page": "uno"},
    ],
)
def test_ruta_infeliz_parametros_invalidos_no_llegan_al_servicio(params):
    """Ruta infeliz: 422 saneado, sin reflejar la entrada."""
    with client_for() as (client, service):
        result = client.get("/clientes", params=params)
    assert result.status_code == 422
    assert all(item["msg"] == "Entrada inválida" for item in result.json()["detail"])
    assert "x" * 20 not in result.text
    service.search.assert_not_called()


@pytest.mark.parametrize(
    "error,status",
    [(ClienteSearchInvalid("privado"), 422), (ClientesUnavailable("privado"), 503)],
)
def test_ruta_infeliz_errores_del_servicio_saneados(error, status):
    with client_for() as (client, service):
        service.search.side_effect = error
        result = client.get("/clientes", params={"buscar": "a"})
    assert result.status_code == status and "privado" not in result.text


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("  Lima  ", "Lima"),
        ("x" * 160, "x" * 160),
    ],
)
def test_ruta_de_borde_normalizacion_del_termino(raw, expected):
    """Ruta de borde: vacío equivale a sin filtro y 160 caracteres es el máximo."""
    assert normalize_term(raw) == expected


@pytest.mark.parametrize("raw", ["x" * 161, "a\x00b", "a\nb"])
def test_ruta_de_borde_terminos_rechazados(raw):
    with pytest.raises(ClienteSearchInvalid):
        normalize_term(raw)


def setup_service():
    session = MagicMock()
    factory = MagicMock()
    factory.return_value.__enter__.return_value = session
    return ClienteService(factory), session


def test_servicio_devuelve_pagina_y_sanea_fallos():
    service, session = setup_service()
    identifier = uuid4()
    session.scalar.return_value = 1
    session.execute.return_value = [Mock(cliente_id=identifier, nombre="Cliente A")]
    page = service.search(" A ", 2, 10)
    assert page.total == 1 and page.page == 2 and page.page_size == 10
    assert page.items[0].cliente_id == identifier
    session.scalar.side_effect = SQLAlchemyError("SQL privado")
    with pytest.raises(ClientesUnavailable) as error:
        service.search(None, 1, 20)
    assert "privado" not in str(error.value)


def test_repositorio_escapa_comodines_ordena_y_acepta_uuid_exacto():
    session = MagicMock()
    session.scalar.return_value = 0
    session.execute.return_value = []
    repository = ClienteRepository(session)
    identifier = uuid4()
    assert repository.search(str(identifier), 1, 20) == ([], 0)
    statement = session.execute.call_args.args[0]
    sql = str(statement)
    assert "lower(cliente.nombre) LIKE lower(" in sql and "ESCAPE" in sql
    assert "cliente.cliente_id =" in sql
    assert "ORDER BY cliente.nombre, cliente.cliente_id" in sql
    repository.search("50%_a", 1, 20)
    pattern = session.execute.call_args.args[0].compile().params["nombre_1"]
    assert pattern == "%50\\%\\_a%"
    repository.search(None, 1, 20)
    assert "WHERE" not in str(session.execute.call_args.args[0])


def test_repositorio_sanea_errores_de_almacenamiento():
    session = MagicMock()
    session.scalar.side_effect = SQLAlchemyError("privado")
    with pytest.raises(ClienteStorageError):
        ClienteRepository(session).search("a", 1, 20)
