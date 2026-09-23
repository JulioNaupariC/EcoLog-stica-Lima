import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from alembic import command
from app.core.config import Settings
from app.db.session import session_factory
from app.main import create_app
from app.models import Auditoria
from app.repositories.usuarios import UsuarioRepository
from app.services.credenciales import CredentialService

pytestmark = pytest.mark.integration


def create_user(factory, email, role):
    with factory.begin() as session:
        return CredentialService(UsuarioRepository(session)).create(
            email, "correct-password", role
        )


def test_authenticated_vehicle_crud_and_real_rbac(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    create_user(factory, "admin-vehicle@example.test", "ADMINISTRADOR")
    create_user(factory, "operator-vehicle@example.test", "OPERADOR")
    app = create_app(
        Settings(app_env="test", database_url=config.attributes["database_url"])
    )
    try:
        with TestClient(app) as client:
            login = client.post(
                "/login",
                json={
                    "email": "admin-vehicle@example.test",
                    "password": "correct-password",
                },
            )
            assert login.status_code == 200
            assert login.json()["rol"] == "ADMINISTRADOR"
            assert client.cookies.get("ecologistica_session") is not None

            created = client.post(
                "/vehiculos",
                json={
                    "placa": " e2e-123 ",
                    "tipo": "CAMIONETA",
                    "capacidad_kg": "1000.00",
                    "capacidad_m3": "8.00",
                    "rendimiento_km_l": "10.000",
                    "factor_co2_kg_km": "0.30000",
                    "anio_fabricacion": 2024,
                },
            )
            assert created.status_code == 201
            vehicle = created.json()
            assert vehicle["placa"] == "E2E-123"
            assert vehicle["estado"] == "ACTIVO"
            vehicle_id = vehicle["vehiculo_id"]

            detail = client.get(f"/vehiculos/{vehicle_id}")
            assert detail.status_code == 200
            assert detail.json()["vehiculo_id"] == vehicle_id

            updated = client.patch(
                f"/vehiculos/{vehicle_id}", json={"rendimiento_km_l": "11.000"}
            )
            assert updated.status_code == 200
            assert updated.json()["rendimiento_km_l"] == "11.000"

            deleted = client.delete(f"/vehiculos/{vehicle_id}")
            assert deleted.status_code == 204
            inactive = client.get(f"/vehiculos/{vehicle_id}")
            assert inactive.status_code == 200
            assert inactive.json()["estado"] == "INACTIVO"

            operator_login = client.post(
                "/login",
                json={
                    "email": "operator-vehicle@example.test",
                    "password": "correct-password",
                },
            )
            assert operator_login.status_code == 200
            assert operator_login.json()["rol"] == "OPERADOR"
            denied = client.delete(f"/vehiculos/{vehicle_id}")
            assert denied.status_code == 403
            assert denied.json() == {"detail": "Acceso denegado"}

        with factory() as session:
            actions = list(
                session.scalars(
                    select(Auditoria.accion).where(Auditoria.entidad_id == vehicle_id)
                )
            )
            assert actions.count("VEHICULO_PARAMETROS_ACTUALIZADOS") == 1
            assert actions.count("VEHICULO_DESACTIVADO") == 1
    finally:
        # Remove disposable test evidence so protected downgrades can clean the schema.
        with factory.begin() as session:
            session.execute(delete(Auditoria))
