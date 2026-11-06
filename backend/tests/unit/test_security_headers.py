"""ECL-84 (OWASP A02/A10): security headers and sanitized 422 everywhere."""

import asyncio
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_authenticated_session
from app.api.pedidos import get_pedido_service
from app.api.security_headers import (
    COMMON,
    CSP_API,
    CSP_DOCS,
    HSTS,
    SecurityHeadersMiddleware,
)
from app.api.vehiculos import get_vehicle_service
from app.core.config import Settings
from app.core.rbac import Identidad, Rol
from app.main import create_app
from app.services.autenticacion import AuthenticatedSession
from app.services.autorizacion import AutorizacionService

FRONTEND = "http://127.0.0.1:5173"


def client(app_env="development", overrides=None):
    settings = Settings(
        database_url=None, app_env=app_env, cors_allowed_origins=[FRONTEND]
    )
    app = create_app(settings)
    identity = Identidad(uuid4(), Rol.ADMINISTRADOR, "ACTIVO")
    app.dependency_overrides[get_authenticated_session] = lambda: AuthenticatedSession(
        uuid4(), identity
    )
    app.dependency_overrides.update(overrides or {})
    return app


def assert_common(response, csp=CSP_API):
    for name, value in COMMON.items():
        assert response.headers[name] == value, name
    assert response.headers["Content-Security-Policy"] == csp


@pytest.mark.parametrize("path", ["/health", "/metrics", "/no-existe", "/pedidos"])
def test_golden_every_response_has_the_headers(path):
    with TestClient(client()) as c:
        response = c.get(path)
    assert_common(response)
    assert "Strict-Transport-Security" not in response.headers


def test_hsts_only_in_production():
    settings = Settings(
        database_url=None,
        app_env="production",
        cors_allowed_origins=["https://ecologistica.example"],
    )
    with TestClient(create_app(settings)) as c:
        response = c.get("/health")
    assert response.headers["Strict-Transport-Security"] == HSTS
    assert_common(response)


def test_docs_keep_frame_protection_but_can_load_their_assets():
    with TestClient(client()) as c:
        docs = c.get("/docs")
        schema = c.get("/openapi.json")
    assert_common(docs, CSP_DOCS)
    assert_common(schema)


def test_edge_cors_preflight_is_unchanged_and_carries_headers():
    with TestClient(client()) as c:
        response = c.options(
            "/pedidos",
            headers={
                "Origin": FRONTEND,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND
    assert response.headers["access-control-allow-credentials"] == "true"
    assert_common(response)


def _run(middleware, scope, inner_headers):
    sent = []

    async def inner(scope, receive, send):
        await send(
            {"type": "http.response.start", "status": 200, "headers": inner_headers}
        )
        await send({"type": "http.response.body", "body": b"{}"})

    async def send(message):
        sent.append(message)

    asyncio.run(middleware(inner)(scope, None, send))
    return sent


def test_an_existing_header_is_not_overwritten():
    sent = _run(
        lambda inner: SecurityHeadersMiddleware(inner, production=False),
        {"type": "http", "path": "/x"},
        [(b"x-frame-options", b"SAMEORIGIN")],
    )
    headers = dict(sent[0]["headers"])
    assert headers[b"x-frame-options"] == b"SAMEORIGIN"
    assert headers[b"x-content-type-options"] == b"nosniff"


def test_non_http_scopes_are_passed_through():
    seen = []

    async def inner(scope, receive, send):
        seen.append(scope["type"])

    asyncio.run(
        SecurityHeadersMiddleware(inner, production=True)(
            {"type": "lifespan"}, None, None
        )
    )
    assert seen == ["lifespan"]


@pytest.mark.parametrize(
    ("path", "dependency", "body", "secreto"),
    [
        (
            "/pedidos",
            get_pedido_service,
            {"direccion": "Calle Secreta 742", "peso_kg": "no-es-numero"},
            "Calle Secreta 742",
        ),
        (
            "/vehiculos",
            get_vehicle_service,
            {"placa": "SECRETA-999999", "tipo": "AVION"},
            "SECRETA-999999",
        ),
    ],
)
def test_happy_and_unhappy_422_never_echo_the_input(path, dependency, body, secreto):
    service = Mock()
    app = client(overrides={dependency: lambda: service})
    with TestClient(app) as c:
        app.state.authorization_service = AutorizacionService(Mock())
        response = c.post(path, json=body)
    assert response.status_code == 422
    assert secreto not in response.text and "no-es-numero" not in response.text
    detail = response.json()["detail"]
    assert detail and all(set(item) == {"loc", "type", "msg"} for item in detail)
    assert {item["msg"] for item in detail} == {"Entrada inválida"}
    service.create.assert_not_called()
