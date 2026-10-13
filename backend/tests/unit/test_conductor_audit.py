"""ECL-48 / RN-015: auditoría de alta y actualización de conductores."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from test_conductor_schemas import payload

from app.models.auditoria import Auditoria
from app.models.conductor import Conductor
from app.models.usuario import Usuario
from app.repositories.auditoria import (
    AuditoriaRepository,
    DetalleConductorActualizado,
    DetalleConductorRegistrado,
    Evento,
    Registro,
)
from app.schemas.conductor import ConductorCreate, ConductorUpdate
from app.services.conductores import ConductorService, ConductorUnavailable

ACTOR = uuid4()


def setup_service():
    session = MagicMock()
    factory = MagicMock()
    factory.begin.return_value.__enter__.return_value = session
    return ConductorService(factory), session


def audit_rows(session):
    return [
        call.args[0]
        for call in session.add.call_args_list
        if isinstance(call.args[0], Auditoria)
    ]


def existing_driver():
    data = ConductorCreate.model_validate(payload()).model_dump(
        exclude={"email", "password"}
    )
    return Conductor(conductor_id=uuid4(), usuario_id=uuid4(), estado="ACTIVO", **data)


def assign_ids_then(session, fail_on=None):
    calls = {"n": 0}

    def flush():
        calls["n"] += 1
        if calls["n"] == fail_on:
            raise SQLAlchemyError("privado")
        for call in session.add.call_args_list:
            obj = call.args[0]
            if isinstance(obj, Usuario) and obj.usuario_id is None:
                obj.usuario_id = uuid4()
            elif isinstance(obj, Conductor) and obj.conductor_id is None:
                obj.conductor_id = uuid4()

    session.flush.side_effect = flush


def test_ruta_dorada_alta_audita_actor_y_conductor_sin_datos_personales():
    """Ruta dorada: el alta registra CONDUCTOR_REGISTRADO con detalle vacío."""
    service, session = setup_service()
    assign_ids_then(session)
    with patch("app.services.conductores.hash_password", return_value="hash"):
        result = service.create(ConductorCreate.model_validate(payload()), ACTOR)
    [row] = audit_rows(session)
    assert row.accion == "CONDUCTOR_REGISTRADO" and row.entidad == "conductor"
    assert row.usuario_id == ACTOR and row.entidad_id == result.conductor_id
    assert row.detalle == {}


def test_ruta_feliz_actualizacion_audita_solo_nombres_de_campos_cambiados():
    """Ruta feliz: solo campos con valor distinto; nunca sus valores."""
    service, session = setup_service()
    driver = existing_driver()
    session.scalar.return_value = driver
    session.get.return_value = Usuario(
        usuario_id=driver.usuario_id, rol="CONDUCTOR", estado="ACTIVO"
    )
    service.update(
        driver.conductor_id,
        ConductorUpdate(telefono="+51911111111", nombre=driver.nombre),
        ACTOR,
    )
    [row] = audit_rows(session)
    assert row.accion == "CONDUCTOR_ACTUALIZADO"
    assert row.detalle == {"campos_modificados": ["telefono"]}
    assert "+51911111111" not in str(row.detalle)


def test_ruta_infeliz_fallo_de_auditoria_aborta_la_operacion_saneada():
    """Ruta infeliz: sin auditoría no hay alta (misma transacción, 503)."""
    service, session = setup_service()
    # Third flush is the audit insert: user, driver, then audit row.
    assign_ids_then(session, fail_on=3)
    with patch("app.services.conductores.hash_password", return_value="hash"):
        with pytest.raises(ConductorUnavailable) as error:
            service.create(ConductorCreate.model_validate(payload()), ACTOR)
    assert "privado" not in str(error.value)


def test_ruta_de_borde_actualizacion_sin_cambios_reales_no_audita():
    """Ruta de borde: enviar los mismos valores no genera evento."""
    service, session = setup_service()
    driver = existing_driver()
    session.scalar.return_value = driver
    session.get.return_value = None
    service.update(driver.conductor_id, ConductorUpdate(nombre=driver.nombre), ACTOR)
    assert audit_rows(session) == []


@pytest.mark.parametrize(
    "registro",
    [
        {
            "usuario_id": None,
            "entidad_id": uuid4(),
            "evento": Evento.CONDUCTOR_REGISTRADO,
            "detalle": DetalleConductorRegistrado(),
        },
        {
            "usuario_id": uuid4(),
            "entidad_id": None,
            "evento": Evento.CONDUCTOR_ACTUALIZADO,
            "detalle": DetalleConductorActualizado(campos_modificados=("dni",)),
        },
        {
            "usuario_id": uuid4(),
            "entidad_id": uuid4(),
            "evento": Evento.CONDUCTOR_REGISTRADO,
            "detalle": DetalleConductorActualizado(campos_modificados=("dni",)),
        },
    ],
)
def test_ruta_infeliz_registros_incoherentes_se_rechazan(registro):
    with pytest.raises(ValidationError):
        Registro(**registro)


@pytest.mark.parametrize(
    "campos", [(), ("dni", "dni"), ("email",), ("password",), ("12345678",)]
)
def test_ruta_de_borde_detalle_solo_admite_nombres_de_campo_unicos(campos):
    with pytest.raises(ValidationError):
        DetalleConductorActualizado(campos_modificados=campos)


def test_repositorio_asigna_entidad_conductor():
    session = MagicMock()
    AuditoriaRepository(session).insert(
        Registro(
            usuario_id=uuid4(),
            entidad_id=uuid4(),
            evento=Evento.CONDUCTOR_ACTUALIZADO,
            detalle=DetalleConductorActualizado(
                campos_modificados=("disponible_desde", "disponible_hasta")
            ),
        )
    )
    row = session.add.call_args.args[0]
    assert row.entidad == "conductor"
    assert row.detalle == {
        "campos_modificados": ["disponible_desde", "disponible_hasta"]
    }
