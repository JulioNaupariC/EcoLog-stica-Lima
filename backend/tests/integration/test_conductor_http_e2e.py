"""Real authenticated HTTP and PostgreSQL rollback checks on an empty test DB."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.core.passwords import hash_password, verify_password
from app.main import create_app
from app.models.auditoria import Auditoria
from app.models.conductor import Conductor
from app.models.usuario import Usuario

pytestmark = pytest.mark.integration
PASSWORD = "synthetic-ecl48-test-password"


def payload(**changes):
    start = datetime.now(timezone.utc) + timedelta(days=1)
    data = dict(
        nombre="Conductor Sintetico",
        dni="01234567",
        licencia_numero="LIC-01",
        licencia_vigente_hasta="2099-12-31",
        experiencia_anios=3,
        telefono="+51987654321",
        punto_partida="Base de prueba",
        disponible_desde=start.isoformat(),
        disponible_hasta=(start + timedelta(hours=9)).isoformat(),
        email="driver@example.test",
        password=PASSWORD,
    )
    data.update(changes)
    return data


def test_real_http_authentication_atomicity_and_driver_privacy(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    try:
        with Session(engine) as session:
            for role in ("ADMINISTRADOR", "OPERADOR", "AUDITOR", "ANALISTA"):
                session.add(
                    Usuario(
                        email=role.lower() + "@example.test",
                        password_hash=hash_password(PASSWORD),
                        rol=role,
                    )
                )
            session.commit()

        app = create_app(
            Settings(database_url=engine.url.render_as_string(hide_password=False))
        )
        with TestClient(app) as client:
            assert client.get("/conductores").status_code == 401
            assert (
                client.post(
                    "/login",
                    json={
                        "email": "administrador@example.test",
                        "password": PASSWORD,
                    },
                ).status_code
                == 200
            )
            response = client.post("/conductores", json=payload())
            assert response.status_code == 201
            driver_id = response.json()["conductor_id"]
            user_id = response.json()["usuario_id"]
            assert response.json()["habilitado_asignacion"] is True
            assert "dni" not in response.json()
            with Session(engine) as session:
                user = session.get(Usuario, UUID(user_id))
                assert user.rol == "CONDUCTOR" and verify_password(
                    PASSWORD, user.password_hash
                )
                counts = (
                    session.scalar(select(func.count()).select_from(Usuario)),
                    session.scalar(select(func.count()).select_from(Conductor)),
                )
            # A duplicate DNI after account insertion must roll back both records.
            assert (
                client.post(
                    "/conductores", json=payload(email="orphan@example.test")
                ).status_code
                == 409
            )
            assert (
                client.post("/conductores", json=payload(dni="87654321")).status_code
                == 409
            )
            with Session(engine) as session:
                assert counts == (
                    session.scalar(select(func.count()).select_from(Usuario)),
                    session.scalar(select(func.count()).select_from(Conductor)),
                )
            assert (
                client.post(
                    "/conductores",
                    json=payload(
                        email="second@example.test",
                        dni="87654321",
                        licencia_vigente_hasta="2000-01-01",
                    ),
                ).json()["habilitado_asignacion"]
                is False
            )
            page = client.get("/conductores?page=1&page_size=1").json()
            assert page["total"] == 2 and len(page["items"]) == 1
            page2 = client.get("/conductores?page=2&page_size=1").json()
            assert page["items"][0]["conductor_id"] != page2["items"][0]["conductor_id"]
            assert "dni" not in page["items"][0]
            assert (
                client.patch(
                    "/conductores/" + driver_id,
                    json={
                        "disponible_desde": None,
                        "disponible_hasta": None,
                    },
                ).json()["habilitado_asignacion"]
                is False
            )
            invalid = client.patch(
                "/conductores/" + driver_id,
                json={
                    "disponible_desde": "2099-01-02T08:00:00Z",
                    "disponible_hasta": "2099-01-01T08:00:00Z",
                },
            )
            assert invalid.status_code == 422
            assert (
                client.patch(
                    "/conductores/" + driver_id, json={"dni": "87654321"}
                ).status_code
                == 409
            )
            with Session(engine) as session:
                driver = session.get(Conductor, UUID(driver_id))
                assert driver.dni == "01234567" and driver.disponible_desde is None
            invalid = client.post(
                "/conductores", json=payload(dni="bad", password_hash="bad")
            )
            assert invalid.status_code == 422 and PASSWORD not in invalid.text
            assert client.get("/conductores/" + str(uuid4())).status_code == 404
            assert client.post("/logout").status_code == 204

            assert (
                client.post(
                    "/login",
                    json={
                        "email": "driver@example.test",
                        "password": PASSWORD,
                    },
                ).status_code
                == 200
            )
            assert client.get("/conductores/" + driver_id).status_code == 200
            own = client.get("/conductores/" + driver_id).json()
            assert not {"dni", "telefono", "licencia_numero"} & own.keys()
            other_id = page2["items"][0]["conductor_id"]
            if other_id == driver_id:
                other_id = page["items"][0]["conductor_id"]
            assert client.get("/conductores/" + other_id).status_code == 403
            assert client.get("/conductores").status_code == 403
            assert (
                client.patch(
                    "/conductores/" + driver_id, json={"nombre": "No"}
                ).status_code
                == 403
            )
            assert client.post("/logout").status_code == 204

            for role in ("auditor", "analista"):
                assert (
                    client.post(
                        "/login",
                        json={
                            "email": role + "@example.test",
                            "password": PASSWORD,
                        },
                    ).status_code
                    == 200
                )
                assert client.get("/conductores").status_code == 403
                assert client.get("/conductores/" + driver_id).status_code == 403
                assert client.post("/conductores", json=payload()).status_code == 403
                assert client.post("/logout").status_code == 204

            assert (
                client.post(
                    "/login",
                    json={
                        "email": "operador@example.test",
                        "password": PASSWORD,
                    },
                ).status_code
                == 200
            )
            assert (
                client.patch(
                    "/conductores/" + driver_id, json={"nombre": "Actualizado"}
                ).status_code
                == 200
            )
            assert (
                client.post(
                    "/conductores",
                    json=payload(
                        dni="11223344",
                        email="third@example.test",
                    ),
                ).status_code
                == 201
            )
            assert client.delete("/conductores/" + driver_id).status_code == 405
            assert client.post("/logout").status_code == 204
    finally:
        # Only disposable evidence in the fixture-validated isolated test DB.
        with Session(engine) as session:
            session.execute(delete(Auditoria))
            session.commit()
