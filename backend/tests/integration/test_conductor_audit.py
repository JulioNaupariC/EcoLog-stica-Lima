"""ECL-48 / RN-015: auditoría real de alta y actualización de conductores."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_conductor_http_e2e import payload
from test_conductor_st024 import driver_http  # noqa: F401  (fixture)

from alembic import command
from app.models.auditoria import Auditoria
from app.models.conductor import Conductor
from app.models.usuario import Usuario
from app.repositories.auditoria import AuditoriaRepository, AuditStorageError

pytestmark = pytest.mark.integration


def driver_events(engine):
    with Session(engine) as session:
        return list(
            session.scalars(
                select(Auditoria)
                .where(Auditoria.accion.like("CONDUCTOR_%"))
                .order_by(Auditoria.creado_en)
            )
        )


def admin_id(engine):
    with Session(engine) as session:
        return session.scalar(
            select(Usuario.usuario_id).where(Usuario.email == "admin@example.test")
        )


def test_ruta_dorada_alta_y_actualizacion_quedan_auditadas(driver_http):  # noqa: F811
    """Ruta dorada: alta + cambio de teléfono y disponibilidad, con actor real."""
    client, engine, _, created = driver_http
    start = datetime.now(timezone.utc) + timedelta(days=1)
    response = client.patch(
        "/conductores/" + created["conductor_id"],
        json={
            "telefono": "+51922222222",
            "disponible_desde": start.isoformat(),
            "disponible_hasta": (start + timedelta(hours=8)).isoformat(),
        },
    )
    assert response.status_code == 200
    registered, updated = driver_events(engine)
    actor = admin_id(engine)
    assert registered.accion == "CONDUCTOR_REGISTRADO"
    assert registered.entidad == "conductor" and registered.detalle == {}
    assert str(registered.entidad_id) == created["conductor_id"]
    assert registered.usuario_id == updated.usuario_id == actor
    assert updated.accion == "CONDUCTOR_ACTUALIZADO"
    assert updated.detalle == {
        "campos_modificados": ["telefono", "disponible_desde", "disponible_hasta"]
    }


def test_ruta_feliz_el_detalle_no_contiene_valores_personales(driver_http):  # noqa: F811
    """Ruta feliz: DNI, nombre y teléfono nunca aparecen en la auditoría."""
    client, engine, _, created = driver_http
    client.patch(
        "/conductores/" + created["conductor_id"],
        json={"nombre": "Nombre Ficticio Nuevo", "dni": "87654321"},
    )
    serialized = " ".join(str(row.detalle) for row in driver_events(engine))
    for value in (payload()["dni"], "87654321", payload()["telefono"], "Ficticio"):
        assert value not in serialized
    assert driver_events(engine)[-1].detalle == {
        "campos_modificados": ["nombre", "dni"]
    }


@pytest.mark.parametrize("operation", ["create", "update"])
def test_ruta_infeliz_sin_auditoria_no_se_persiste_el_cambio(
    driver_http,  # noqa: F811
    monkeypatch,
    operation,
):
    """Ruta infeliz: si la auditoría falla, 503 y la transacción se revierte."""
    client, engine, _, created = driver_http
    original_insert = AuditoriaRepository.insert

    def failing_insert(self, registro):
        if registro.evento.value.startswith("CONDUCTOR_"):
            raise AuditStorageError("privado")
        return original_insert(self, registro)

    monkeypatch.setattr(AuditoriaRepository, "insert", failing_insert)
    with Session(engine) as session:
        drivers_before = session.scalar(select(func.count()).select_from(Conductor))
    if operation == "create":
        response = client.post(
            "/conductores",
            json=payload(dni="11223344", email="otro@example.test"),
        )
    else:
        response = client.patch(
            "/conductores/" + created["conductor_id"], json={"nombre": "No guardar"}
        )
    assert response.status_code == 503 and "privado" not in response.text
    with Session(engine) as session:
        assert (
            session.scalar(select(func.count()).select_from(Conductor))
            == drivers_before
        )
        assert (
            session.scalar(
                select(Conductor.nombre).where(
                    Conductor.conductor_id == created["conductor_id"]
                )
            )
            == payload()["nombre"]
        )
    assert len(driver_events(engine)) == 1


def test_ruta_de_borde_mismos_valores_y_peticion_invalida_no_auditan(
    driver_http,  # noqa: F811
):
    """Ruta de borde: PATCH sin cambios reales o inválido no crea eventos."""
    client, engine, _, created = driver_http
    path = "/conductores/" + created["conductor_id"]
    assert client.patch(path, json={"nombre": payload()["nombre"]}).status_code == 200
    assert client.patch(path, json={"experiencia_anios": -1}).status_code == 422
    assert [row.accion for row in driver_events(engine)] == ["CONDUCTOR_REGISTRADO"]


def test_migracion_0010_upgrade_downgrade_limpio(migration_database):
    engine, config = migration_database
    command.upgrade(config, "0010_extend_driver_audit_events")
    with engine.connect() as connection:
        constraint = connection.scalar(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'ck_auditoria_accion' "
                "AND conrelid = 'auditoria'::regclass"
            )
        )
    assert "CONDUCTOR_REGISTRADO" in constraint
    assert "CONDUCTOR_ACTUALIZADO" in constraint
    assert "VEHICULO_DESACTIVADO" in constraint
    command.downgrade(config, "0009_driver_stop_order")
    with engine.connect() as connection:
        constraint = connection.scalar(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'ck_auditoria_accion' "
                "AND conrelid = 'auditoria'::regclass"
            )
        )
    assert "CONDUCTOR_" not in constraint
    command.upgrade(config, "head")
    command.check(config)


def test_migracion_0010_downgrade_rechaza_borrar_auditoria_existente(
    migration_database,
):
    engine, config = migration_database
    command.upgrade(config, "0010_extend_driver_audit_events")
    with engine.begin() as connection:
        user_id = connection.scalar(
            text(
                "INSERT INTO usuario (email, password_hash, rol) "
                "VALUES ('driver-audit@example.test', 'x', 'ADMINISTRADOR') "
                "RETURNING usuario_id"
            )
        )
        connection.execute(
            text(
                "INSERT INTO auditoria (usuario_id, entidad, entidad_id, accion, "
                "detalle) VALUES (:user_id, 'conductor', gen_random_uuid(), "
                "'CONDUCTOR_REGISTRADO', '{}'::jsonb)"
            ),
            {"user_id": user_id},
        )
    with pytest.raises(DBAPIError, match="manual treatment"):
        command.downgrade(config, "0009_driver_stop_order")
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0010_extend_driver_audit_events"
        )
        assert (
            connection.scalar(
                text("SELECT count(*) FROM auditoria WHERE entidad = 'conductor'")
            )
            == 1
        )
        # Fixture-only cleanup so the shared teardown can downgrade to base.
        connection.execute(text("DELETE FROM auditoria"))
