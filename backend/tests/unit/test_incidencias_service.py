"""ECL-73 incident service and schema, with persistence replaced by mocks."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import CheckConstraint
from sqlalchemy.exc import SQLAlchemyError

from app.core import incidencias as constants
from app.core.incidencias import (
    OBSERVACION_MAX,
    OCURRIDA_MAX_ANTIGUEDAD,
    OCURRIDA_MAX_FUTURO,
    EstadoIncidencia,
    SeveridadIncidencia,
    TipoIncidencia,
)
from app.models.auditoria import Auditoria
from app.models.incidencia import Incidencia
from app.repositories.auditoria import DetalleIncidenciaRegistrada, Evento, Registro
from app.repositories.incidencias import (
    IncidenciaDuplicateOperation,
    IncidenciaRow,
    IncidenciaStorageError,
    StoredIncidencia,
)
from app.schemas.incidencia import IncidenciaCreate
from app.services import incidencias as module
from app.services.incidencias import (
    LIMA,
    IncidenciaConflicto,
    IncidenciaInvalida,
    IncidenciaService,
    IncidenciaSinConductor,
    IncidenciaUnavailable,
)

NOW = datetime(2026, 10, 27, 14, 30, tzinfo=timezone.utc)
USER = uuid4()
CONDUCTOR = uuid4()
STOP = uuid4()


def payload(**changes):
    values = {
        "operation_id": uuid4(),
        "tipo": "AVERIA",
        "severidad": "ALTA",
        "ocurrida_en": NOW - timedelta(minutes=10),
        "latitud": -12.0464,
        "longitud": -77.0428,
        "parada_id": None,
        "observacion": "Llanta pinchada",
    }
    values.update(changes)
    return IncidenciaCreate.model_validate(values)


def stored_from(data: IncidenciaCreate, **changes) -> StoredIncidencia:
    values = {
        "incidencia_id": uuid4(),
        "operation_id": data.operation_id,
        "conductor_id": CONDUCTOR,
        "parada_id": data.parada_id,
        "tipo": data.tipo.value,
        "severidad": data.severidad.value,
        "ocurrida_en": data.ocurrida_en.astimezone(timezone.utc),
        "latitud": data.latitud + 1e-12,
        "longitud": data.longitud,
        "observacion": data.observacion,
        "estado": "PENDIENTE_VALIDACION",
        "registrada_en": NOW,
    }
    values.update(changes)
    return StoredIncidencia(**values)


@pytest.fixture
def fakes(monkeypatch):
    repository = Mock()
    repository.conductor_id_for.return_value = CONDUCTOR
    repository.find_by_operation.return_value = None
    repository.stop_belongs_to.return_value = True

    def add(incidencia, latitud, longitud):
        incidencia.incidencia_id = uuid4()
        incidencia.estado = "PENDIENTE_VALIDACION"
        incidencia.registrada_en = NOW
        return incidencia

    repository.add.side_effect = add
    audit_rows = []
    audit = Mock()
    audit.insert.side_effect = audit_rows.append
    monkeypatch.setattr(module, "IncidenciaRepository", lambda session: repository)
    monkeypatch.setattr(module, "AuditoriaRepository", lambda session: audit)
    factory = MagicMock()
    return SimpleNamespace(
        service=IncidenciaService(factory),
        factory=factory,
        repository=repository,
        audit_rows=audit_rows,
    )


# --- Constantes únicas ------------------------------------------------------


def test_single_source_of_catalogues_and_limits():
    assert constants.TIPOS == (
        "TRAFICO",
        "AVERIA",
        "ACCIDENTE",
        "CLIMA",
        "SEGURIDAD",
        "OTRO",
    )
    assert constants.SEVERIDADES == ("BAJA", "MEDIA", "ALTA")
    assert constants.ESTADOS == ("PENDIENTE_VALIDACION", "VALIDADA", "DESCARTADA")
    assert (OBSERVACION_MAX, OCURRIDA_MAX_FUTURO, OCURRIDA_MAX_ANTIGUEDAD) == (
        500,
        timedelta(minutes=5),
        timedelta(hours=24),
    )
    checks = {
        c.name: str(c.sqltext)
        for c in Incidencia.__table__.constraints
        if isinstance(c, CheckConstraint)
    }
    for value in (*constants.TIPOS, *constants.SEVERIDADES, *constants.ESTADOS):
        assert any(f"'{value}'" in text for text in checks.values())
    assert f"<= {OBSERVACION_MAX}" in checks["ck_incidencia_observacion"]
    assert "'INCIDENCIA_REGISTRADA'" in str(
        next(
            c.sqltext
            for c in Auditoria.__table__.constraints
            if c.name == "ck_auditoria_accion"
        )
    )


# --- Ruta dorada --------------------------------------------------------------


def test_golden_registers_pending_incident_and_audits_without_personal_data(fakes):
    data = payload(parada_id=STOP)

    ack, created = fakes.service.registrar(USER, data, now=NOW)

    assert created is True
    assert ack.estado is EstadoIncidencia.PENDIENTE_VALIDACION
    assert ack.operation_id == data.operation_id
    assert ack.registrada_en.utcoffset() == timedelta(hours=-5)
    fakes.repository.conductor_id_for.assert_called_once_with(USER)
    fakes.repository.stop_belongs_to.assert_called_once_with(STOP, USER)
    [incidencia, lat, lon] = fakes.repository.add.call_args.args
    assert (incidencia.conductor_id, incidencia.parada_id) == (CONDUCTOR, STOP)
    assert (lat, lon) == (data.latitud, data.longitud)
    [row] = fakes.audit_rows
    assert row.evento is Evento.INCIDENCIA_REGISTRADA
    assert (row.usuario_id, row.entidad_id) == (USER, ack.incidencia_id)
    assert row.detalle == DetalleIncidenciaRegistrada(
        tipo=TipoIncidencia.AVERIA,
        severidad=SeveridadIncidencia.ALTA,
        con_parada=True,
        con_observacion=True,
    )
    dumped = str(row.model_dump())
    assert "Llanta" not in dumped and "-12.0464" not in dumped


# --- Ruta feliz: reenvío idempotente -------------------------------------------


def test_happy_same_operation_and_content_returns_original_without_duplicating(
    fakes,
):
    data = payload()
    stored = stored_from(data)
    fakes.repository.find_by_operation.return_value = stored

    # Even far outside the time window: the original answer is kept.
    ack, created = fakes.service.registrar(USER, data, now=NOW + timedelta(days=3))

    assert created is False
    assert ack.incidencia_id == stored.incidencia_id
    assert ack.registrada_en == NOW
    fakes.repository.add.assert_not_called()
    assert fakes.audit_rows == []


# --- Ruta infeliz ----------------------------------------------------------------


@pytest.mark.parametrize(
    "changes",
    [
        {"tipo": "TRAFICO"},
        {"severidad": "BAJA"},
        {"ocurrida_en": NOW - timedelta(minutes=11)},
        {"latitud": -12.05},
        {"longitud": -77.05},
        {"parada_id": STOP},
        {"observacion": None},
        {"conductor_id": uuid4()},
    ],
)
def test_unhappy_same_operation_with_different_content_conflicts(fakes, changes):
    data = payload()
    stored_changes = {
        key: (value.value if hasattr(value, "value") else value)
        for key, value in changes.items()
    }
    fakes.repository.find_by_operation.return_value = stored_from(
        data, **stored_changes
    )
    with pytest.raises(IncidenciaConflicto):
        fakes.service.registrar(USER, data, now=NOW)
    fakes.repository.add.assert_not_called()


def test_unhappy_user_without_driver_profile_is_refused(fakes):
    fakes.repository.conductor_id_for.return_value = None
    with pytest.raises(IncidenciaSinConductor):
        fakes.service.registrar(USER, payload(), now=NOW)
    fakes.repository.add.assert_not_called()


# --- Rutas de borde --------------------------------------------------------------


@pytest.mark.parametrize(
    "ocurrida_en,valid",
    [
        (NOW + OCURRIDA_MAX_FUTURO, True),
        (NOW + OCURRIDA_MAX_FUTURO + timedelta(seconds=1), False),
        (NOW - OCURRIDA_MAX_ANTIGUEDAD, True),
        (NOW - OCURRIDA_MAX_ANTIGUEDAD - timedelta(seconds=1), False),
    ],
)
def test_edge_time_window_limits(fakes, ocurrida_en, valid):
    data = payload(ocurrida_en=ocurrida_en)
    if valid:
        assert fakes.service.registrar(USER, data, now=NOW)[1] is True
    else:
        with pytest.raises(IncidenciaInvalida):
            fakes.service.registrar(USER, data, now=NOW)
        fakes.repository.add.assert_not_called()


def test_edge_time_window_compares_instants_across_time_zones(fakes):
    lima = (NOW - timedelta(minutes=1)).astimezone(LIMA)
    assert fakes.service.registrar(USER, payload(ocurrida_en=lima), now=NOW)[1]


def test_edge_stop_of_another_driver_is_invalid(fakes):
    fakes.repository.stop_belongs_to.return_value = False
    with pytest.raises(IncidenciaInvalida):
        fakes.service.registrar(USER, payload(parada_id=STOP), now=NOW)
    fakes.repository.add.assert_not_called()


def test_edge_without_stop_skips_the_ownership_query(fakes):
    fakes.service.registrar(USER, payload(observacion=None), now=NOW)
    fakes.repository.stop_belongs_to.assert_not_called()
    assert fakes.audit_rows[0].detalle.con_observacion is False
    assert fakes.audit_rows[0].detalle.con_parada is False


@pytest.mark.parametrize("same", [True, False])
def test_edge_concurrent_duplicate_is_compared_like_a_retry(fakes, same):
    data = payload()
    fakes.repository.add.side_effect = IncidenciaDuplicateOperation()
    fakes.repository.find_by_operation.side_effect = [
        None,
        stored_from(data) if same else stored_from(data, tipo="OTRO"),
    ]
    if same:
        ack, created = fakes.service.registrar(USER, data, now=NOW)
        assert (ack.operation_id, created) == (data.operation_id, False)
    else:
        with pytest.raises(IncidenciaConflicto):
            fakes.service.registrar(USER, data, now=NOW)


def test_edge_concurrent_duplicate_that_vanished_is_unavailable(fakes):
    fakes.repository.add.side_effect = IncidenciaDuplicateOperation()
    fakes.repository.find_by_operation.side_effect = [None, None]
    with pytest.raises(IncidenciaUnavailable):
        fakes.service.registrar(USER, payload(), now=NOW)


def test_edge_concurrent_retry_storage_failure_is_unavailable(fakes):
    fakes.repository.add.side_effect = IncidenciaDuplicateOperation()
    fakes.repository.find_by_operation.side_effect = [
        None,
        IncidenciaStorageError("private"),
    ]
    with pytest.raises(IncidenciaUnavailable):
        fakes.service.registrar(USER, payload(), now=NOW)


@pytest.mark.parametrize(
    "failure", [IncidenciaStorageError("private"), SQLAlchemyError("private")]
)
def test_edge_storage_failures_are_sanitized(fakes, failure):
    fakes.repository.conductor_id_for.side_effect = failure
    with pytest.raises(IncidenciaUnavailable) as error:
        fakes.service.registrar(USER, payload(), now=NOW)
    assert "private" not in str(error.value)


def test_registrar_defaults_to_the_current_time(fakes):
    data = payload(ocurrida_en=datetime.now(timezone.utc))
    assert fakes.service.registrar(USER, data)[1] is True


# --- Listado ----------------------------------------------------------------------


def test_list_maps_rows_to_lima_time_without_personal_data(fakes):
    row = IncidenciaRow(
        uuid4(),
        "AVERIA",
        "ALTA",
        NOW,
        NOW + timedelta(minutes=1),
        CONDUCTOR,
        "Conductora Demo Uno",
        -12.0464,
        -77.0428,
        "Llanta pinchada",
        "PENDIENTE_VALIDACION",
    )
    fakes.repository.list_page.return_value = ([row], 41)

    page = fakes.service.listar(EstadoIncidencia.PENDIENTE_VALIDACION, 3, 20)

    fakes.repository.list_page.assert_called_once_with("PENDIENTE_VALIDACION", 3, 20)
    assert (page.page, page.page_size, page.total) == (3, 20, 41)
    [item] = page.items
    assert item.ocurrida_en.utcoffset() == timedelta(hours=-5)
    assert item.conductor.model_dump() == {
        "conductor_id": CONDUCTOR,
        "nombre": "Conductora Demo Uno",
    }


def test_list_storage_failure_is_sanitized(fakes):
    fakes.repository.list_page.side_effect = IncidenciaStorageError("private")
    with pytest.raises(IncidenciaUnavailable):
        fakes.service.listar(EstadoIncidencia.PENDIENTE_VALIDACION, 1, 20)


# --- Esquema ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "changes",
    [
        {"latitud": 90.0001},
        {"latitud": -90.0001},
        {"longitud": 180.5},
        {"longitud": -180.5},
        {"latitud": float("nan")},
        {"longitud": float("inf")},
        {"ocurrida_en": datetime(2026, 10, 27, 9, 15)},
        {"observacion": "x" * (OBSERVACION_MAX + 1)},
        {"tipo": "INCENDIO"},
        {"severidad": "CRITICA"},
        {"operation_id": "no-es-uuid"},
        {"conductor_id": str(uuid4())},
    ],
)
def test_edge_schema_rejects_invalid_input(changes):
    values = payload().model_dump()
    values.update(changes)
    with pytest.raises(ValidationError):
        IncidenciaCreate.model_validate(values)


def test_edge_schema_limits_and_blank_observation():
    assert payload(observacion="x" * OBSERVACION_MAX).observacion
    assert payload(observacion="   ").observacion is None
    assert payload(observacion="  texto  ").observacion == "texto"
    assert payload(latitud=-90, longitud=180).latitud == -90


def test_incident_audit_requires_actor_and_entity():
    detail = DetalleIncidenciaRegistrada(
        tipo=TipoIncidencia.OTRO,
        severidad=SeveridadIncidencia.BAJA,
        con_parada=False,
        con_observacion=False,
    )
    for usuario_id, entidad_id in ((None, uuid4()), (uuid4(), None)):
        with pytest.raises(ValueError):
            Registro(
                usuario_id=usuario_id,
                entidad_id=entidad_id,
                evento=Evento.INCIDENCIA_REGISTRADA,
                detalle=detail,
            )
    with pytest.raises(ValueError):
        Registro(
            usuario_id=uuid4(),
            entidad_id=uuid4(),
            evento=Evento.CONDUCTOR_REGISTRADO,
            detalle=detail,
        )
