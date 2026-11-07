"""ECL-109 (Green IT): every listing serves 12 rows per page by default.

Checked on the published OpenAPI contract, so the frontend and the API agree
without mocking each service.
"""

import pytest

from app.core.config import Settings
from app.main import create_app

LISTINGS = {
    "/vehiculos": 100,
    "/conductores": 100,
    "/usuarios": 100,
    "/clientes": 50,
    "/incidencias": 100,
}


@pytest.fixture(scope="module")
def openapi():
    return create_app(Settings(database_url=None)).openapi()


def query_parameter(openapi, path, name):
    parameters = openapi["paths"][path]["get"]["parameters"]
    return next(item["schema"] for item in parameters if item["name"] == name)


@pytest.mark.parametrize("path,maximum", LISTINGS.items())
def test_listing_defaults_to_twelve_rows(openapi, path, maximum):
    page_size = query_parameter(openapi, path, "page_size")
    assert page_size["default"] == 12
    assert page_size["minimum"] == 1
    assert page_size["maximum"] == maximum
    page = query_parameter(openapi, path, "page")
    assert page["default"] == 1
    assert page["minimum"] == 1


@pytest.mark.parametrize("path", LISTINGS)
def test_listing_returns_a_page_envelope(openapi, path):
    response = openapi["paths"][path]["get"]["responses"]["200"]
    reference = response["content"]["application/json"]["schema"]["$ref"]
    schema = openapi["components"]["schemas"][reference.rsplit("/", 1)[-1]]
    assert {"items", "page", "page_size", "total"} <= set(schema["properties"])
