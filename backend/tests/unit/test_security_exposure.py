"""ECL-32 exposure contract for resources that exist today.

RNF-004 is only partially automatable at this stage. The current API has no
driver/customer/order response carrying DNI or contact data. Those literal
field-level checks remain pending until the corresponding resources exist.
"""

from app.api.auth import LoginResponse
from app.schemas.vehiculo import VehicleResponse

RESTRICTED_FIELDS = {
    "password",
    "password_hash",
    "token",
    "cookie",
    "email",
    "dni",
    "contacto",
}


def test_login_public_schema_exposes_identity_role_and_expiration_metadata():
    fields = set(LoginResponse.model_fields)

    assert fields == {"usuario_id", "rol", "expires_at"}
    assert fields.isdisjoint(RESTRICTED_FIELDS)


def test_vehicle_public_schema_is_exact_and_contains_no_account_secrets():
    fields = set(VehicleResponse.model_fields)

    assert fields == {
        "vehiculo_id",
        "placa",
        "tipo",
        "capacidad_kg",
        "capacidad_m3",
        "rendimiento_km_l",
        "factor_co2_kg_km",
        "anio_fabricacion",
        "estado",
    }
    assert fields.isdisjoint(RESTRICTED_FIELDS)
