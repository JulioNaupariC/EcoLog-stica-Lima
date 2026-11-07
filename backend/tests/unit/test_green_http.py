"""ECL-110 (Green IT): GZip compression and ETag revalidation in the API."""

import asyncio
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.conditional_get import ConditionalGetMiddleware, _matches
from app.api.dependencies import get_authenticated_session
from app.api.vehiculos import get_vehicle_service
from app.core.config import Settings
from app.core.rbac import Identidad, Rol
from app.main import GZIP_MINIMUM_BYTES, create_app
from app.models.vehiculo import Vehiculo
from app.services.autenticacion import AuthenticatedSession
from app.services.autorizacion import AutorizacionService

FRONTEND = "http://127.0.0.1:5173"


def vehicles(count):
    return [
        Vehiculo(
            vehiculo_id=uuid4(),
            placa=f"ECO{index:03d}",
            tipo="CAMIONETA",
            capacidad_kg=Decimal("800.00"),
            capacidad_m3=Decimal("4.00"),
            rendimiento_km_l=Decimal("11.000"),
            factor_co2_kg_km=Decimal("0.24364"),
            anio_fabricacion=2024,
            estado="ACTIVO",
        )
        for index in range(count)
    ]


@pytest.fixture
def api():
    app = create_app(Settings(database_url=None, cors_allowed_origins=[FRONTEND]))
    identity = Identidad(uuid4(), Rol.OPERADOR, "ACTIVO")
    app.dependency_overrides[get_authenticated_session] = lambda: AuthenticatedSession(
        uuid4(), identity
    )
    service = Mock()
    app.dependency_overrides[get_vehicle_service] = lambda: service
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(Mock())
        yield client, service


# --- GZip -------------------------------------------------------------------


def test_golden_large_json_is_gzip_compressed(api):
    client, service = api
    service.list_all.return_value = vehicles(12)
    plain = client.get("/vehiculos", headers={"Accept-Encoding": "identity"})
    compressed = client.get("/vehiculos", headers={"Accept-Encoding": "gzip"})
    assert len(plain.content) >= GZIP_MINIMUM_BYTES
    assert "content-encoding" not in plain.headers
    assert compressed.headers["content-encoding"] == "gzip"
    assert compressed.json() == plain.json()  # httpx decodes transparently
    raw = int(compressed.headers["content-length"])
    assert raw < len(plain.content)


def test_small_responses_stay_uncompressed(api):
    client, _ = api
    response = client.get("/health", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert "content-encoding" not in response.headers


# --- ETag -------------------------------------------------------------------


def test_happy_catalogue_gets_weak_etag_and_revalidation_policy(api):
    client, service = api
    service.list_all.return_value = vehicles(2)
    response = client.get("/vehiculos")
    assert response.status_code == 200
    assert response.headers["etag"].startswith('W/"')
    assert response.headers["cache-control"] == "private, no-cache"
    # Security headers from ECL-84 still reach the response.
    assert response.headers["x-content-type-options"] == "nosniff"


def test_same_etag_answers_304_without_body(api):
    client, service = api
    service.list_all.return_value = vehicles(3)
    first = client.get("/vehiculos")
    again = client.get("/vehiculos", headers={"If-None-Match": first.headers["etag"]})
    assert again.status_code == 304
    assert again.content == b""
    assert again.headers["etag"] == first.headers["etag"]
    assert "content-type" not in again.headers


def test_unhappy_changed_data_returns_200_with_new_etag(api):
    client, service = api
    service.list_all.return_value = vehicles(1)
    first = client.get("/vehiculos")
    service.list_all.return_value = vehicles(2)
    second = client.get("/vehiculos", headers={"If-None-Match": first.headers["etag"]})
    assert second.status_code == 200
    assert second.headers["etag"] != first.headers["etag"]
    assert len(second.json()) == 2


def test_etag_is_stable_across_gzip_and_identity(api):
    client, service = api
    service.list_all.return_value = vehicles(12)
    gz = client.get("/vehiculos", headers={"Accept-Encoding": "gzip"})
    plain = client.get("/vehiculos", headers={"Accept-Encoding": "identity"})
    assert gz.headers["etag"] == plain.headers["etag"]
    revalidated = client.get(
        "/vehiculos",
        headers={"Accept-Encoding": "gzip", "If-None-Match": plain.headers["etag"]},
    )
    assert revalidated.status_code == 304


def test_edge_personal_and_no_store_responses_get_no_etag():
    app = create_app(Settings(database_url=None))
    identity = Identidad(uuid4(), Rol.OPERADOR, "ACTIVO")
    app.dependency_overrides[get_authenticated_session] = lambda: AuthenticatedSession(
        uuid4(), identity
    )
    with TestClient(app) as client:
        app.state.authorization_service = AutorizacionService(Mock())
        no_store = client.get("/optimizaciones")  # simulated routes: no-store
        metrics = client.get("/metrics")
    assert no_store.status_code == 200 and "etag" not in no_store.headers
    assert "etag" not in metrics.headers


def test_errors_and_other_methods_are_untouched(api):
    client, _ = api
    response = client.post("/vehiculos", json={})
    assert response.status_code == 422 and "etag" not in response.headers


def test_cors_preflight_is_unchanged(api):
    client, _ = api
    response = client.options(
        "/vehiculos",
        headers={"Origin": FRONTEND, "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND
    assert "etag" not in response.headers


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, False),
        ("", False),
        ("*", True),
        ('W/"abc"', True),
        ('"abc"', True),
        ('"zzz", W/"abc"', True),
        ('"zzz"', False),
    ],
)
def test_weak_comparison(header, expected):
    assert _matches(header, 'W/"abc"') is expected


def test_non_200_eligible_response_passes_body_through():
    sent = []

    async def app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": b'{"detail":"x"}'})

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "method": "GET", "path": "/vehiculos/x", "headers": []}
    asyncio.run(ConditionalGetMiddleware(app)(scope, None, send))
    assert sent[0]["status"] == 404
    assert all(name != b"etag" for name, _ in sent[0]["headers"])
    assert sent[1]["body"] == b'{"detail":"x"}'


def test_streamed_eligible_body_is_joined_before_tagging():
    sent = []

    async def app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": b"[1,", "more_body": True})
        await send({"type": "http.response.body", "body": b"2]"})

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "method": "GET", "path": "/vehiculos", "headers": []}
    asyncio.run(ConditionalGetMiddleware(app)(scope, None, send))
    assert dict(sent[0]["headers"])[b"etag"].startswith(b'W/"')
    assert sent[1]["body"] == b"[1,2]"


def test_non_http_scope_passes_through():
    seen = []

    async def app(scope, receive, send):
        seen.append(scope["type"])

    asyncio.run(ConditionalGetMiddleware(app)({"type": "lifespan"}, None, None))
    assert seen == ["lifespan"]
