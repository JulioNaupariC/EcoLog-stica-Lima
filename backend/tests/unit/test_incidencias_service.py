"""ECL-73 incident service and schema against the ECL-72 BDD (I01–I16).

Persistence is replaced by mocks; the clock is fixed at T0 from the BDD.
"""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock
from uuid import UUID, uuid1, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.exc import SQLAlchemyError

from app.core import incidencias as constants
from app.core.incidencias import (
    OBSERVACION_MAX,
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
    IncidenciaParadaAjena,
    IncidenciaService,
    IncidenciaSinConductor,
    IncidenciaUnavailable,
)

T0 = datetime(2026, 10, 27, 9, 16, 2, tzinfo=LIMA)
USER = uuid4()
CONDUCTOR = uuid4()
STOP = uuid4()
OPERATION = UUID("2d7d7ad5-57e1-4b17-9c8d-5094a6fc7a01")
FIXTURE = {
    "operation_id": str(OPERATION),
    "tipo": "AVERIA",
    "severidad": "ALTA",
    "ocurrida_en": "2026-10-27T09:15:00-05:00",
    "latitud": -12.0464,
    "longitud": -77.0428,
    "observacion": "Llanta pinchada: reporte de prueba",
}


def payload(**changes) -> IncidenciaCreate:
    return IncidenciaCreate.model_validate_json(json.dumps({**FIXTURE, **changes}))


def stored_from(data: IncidenciaCreate, **changes) -> StoredIncidencia:
    values = {
        "incidencia_id": uuid4(),
        "operation_id": data.operation_id,
        "conductor_id": CONDUCTOR,
        "parada_id": data.parada_id,
        "tipo": data.tipo.value,
        "severidad": data.severidad.value,
        "ocurrida_en": data.ocurrida_en.astimezone(timezone.utc),
        "latitud": data.latitud,
        "longitud": data.longitud,
        "observacion": data.observacion,
        "estado": "PENDIENTE_VALIDACION",
        "registrada_en": T0,
    }
    values.update(changes)
    return StoredIncidencia(**values)


@pytest.fixture
def fakes(monkeypatch):
    repository = Mock()
    repository.conductor_id_for.return_value = CONDUCTOR
    repository.find_by_operation.return_value = None
    repository.stop_owner.return_value = USER

    def add(incidencia, latitud, longitud):
        incidencia.incidencia_id = uuid4()
        incidencia.estado = "PENDIENTE_VALIDACION"
        incidencia.registrada_en = T0
        return incidencia

    repository.add.side_effect = add
    audit_rows = []
    audit = Mock()
    audit.insert.side_effect = audit_rows.append
    monkeypatch.setattr(module, "IncidenciaRepository", lambda session: repository)
    monkeypatch.setattr(module, "AuditoriaRepository", lambda session: audit)
    monkeypatch.setattr(module, "utc_now", lambda: T0.astimezone(timezone.utc))
    return SimpleNamespace(
        service=IncidenciaService(MagicMock()),
        repository=repository,
        audit_rows=audit_rows,
    )


# --- Fuente única de catálogos y límites -------------------------------------


def test_catalogos_y_limites_salen_de_un_solo_modulo():
    assert constants.TIPOS == (
        "TRAFICO",
        "AVERIA",
        "ACCIDENTE",
        "CLIMA",
        "SEGURIDAD",
        "OTRO",
    )
    assert constants.SEVERIDADES == ("BAJA", "MEDIA", "ALTA")
    assert (OBSERVACION_MAX, OCURRIDA_MAX_FUTURO) == (500, timedelta(minutes=5))
    assert not hasattr(constants, "OCURRIDA_MAX_ANTIGUEDAD")
    assert (constants.PAGE_SIZE_DEFAULT, constants.PAGE_SIZE_MAX) == (20, 100)
    table = Incidencia.__table__
    checks = {
        c.name: str(c.sqltext)
        for c in table.constraints
        if isinstance(c, CheckConstraint)
    }
    for value in (*constants.TIPOS, *constants.SEVERIDADES, *constants.ESTADOS):
        assert any(f"'{value}'" in text for text in checks.values())
    assert f"<= {OBSERVACION_MAX}" in checks["ck_incidencia_observacion"]
    [unique] = [c for c in table.constraints if isinstance(c, UniqueConstraint)]
    assert [column.name for column in unique.columns] == [
        "conductor_id",
        "operation_id",
    ]
    assert not table.c.observacion.nullable
    assert "'INCIDENCIA_REGISTRADA'" in str(
        next(
            c.sqltext
            for c in Auditoria.__table__.constraints
            if c.name == "ck_auditoria_accion"
        )
    )


# --- I01 / I03: alta válida --------------------------------------------------


def test_I01_alta_sin_parada_queda_pendiente_y_auditada_sin_datos_personales(fakes):
    data = payload()

    ack, created = fakes.service.registrar(USER, data)

    assert created is True
    assert ack.estado is EstadoIncidencia.PENDIENTE_VALIDACION
    assert ack.operation_id == OPERATION
    assert ack.registrada_en.utcoffset() == timedelta(hours=-5)
    [incidencia, lat, lon] = fakes.repository.add.call_args.args
    assert (incidencia.conductor_id, incidencia.parada_id) == (CONDUCTOR, None)
    assert (lat, lon) == (-12.0464, -77.0428)
    fakes.repository.stop_owner.assert_not_called()
    [row] = fakes.audit_rows
    assert row.evento is Evento.INCIDENCIA_REGISTRADA
    assert (row.usuario_id, row.entidad_id) == (USER, ack.incidencia_id)
    assert row.detalle == DetalleIncidenciaRegistrada(
        tipo=TipoIncidencia.AVERIA,
        severidad=SeveridadIncidencia.ALTA,
        con_parada=False,
        con_observacion=True,
    )
    dumped = str(row.model_dump())
    assert "Llanta" not in dumped and "-12.0464" not in dumped


def test_I03_alta_con_parada_propia(fakes):
    ack, created = fakes.service.registrar(USER, payload(parada_id=str(STOP)))
    assert created and ack.estado is EstadoIncidencia.PENDIENTE_VALIDACION
    fakes.repository.stop_owner.assert_called_once_with(STOP)
    assert fakes.repository.add.call_args.args[0].parada_id == STOP
    assert fakes.audit_rows[0].detalle.con_parada is True


# --- I13 / I16: idempotencia por (conductor, operation_id) -------------------


@pytest.mark.parametrize(
    "replay",
    [
        {},
        {"ocurrida_en": "2026-10-27T14:15:00Z"},
        {"latitud": -12.0464, "longitud": -77.0428},
    ],
)
def test_I13_reenvio_equivalente_devuelve_200_sin_duplicar_ni_revalidar(fakes, replay):
    original = payload()
    stored = stored_from(original)
    fakes.repository.find_by_operation.return_value = stored
    # The stop context may have changed since the original was stored.
    fakes.repository.stop_owner.side_effect = AssertionError("not revalidated")

    ack, created = fakes.service.registrar(
        USER, payload(**replay), now=T0 + timedelta(days=30)
    )

    assert created is False
    assert (ack.incidencia_id, ack.registrada_en) == (stored.incidencia_id, T0)
    fakes.repository.find_by_operation.assert_called_once_with(CONDUCTOR, OPERATION)
    fakes.repository.add.assert_not_called()
    assert fakes.audit_rows == []


def test_I13_coordenadas_enteras_y_decimales_son_equivalentes(fakes):
    original = payload(latitud=-12, longitud=-77)
    fakes.repository.find_by_operation.return_value = stored_from(original)
    assert (
        fakes.service.registrar(USER, payload(latitud=-12.0, longitud=-77.0))[1]
        is False
    )


@pytest.mark.parametrize("omitted", ["null", "missing", "empty"])
def test_I13_observacion_omitida_null_o_vacia_es_equivalente(fakes, omitted):
    base = {key: value for key, value in FIXTURE.items() if key != "observacion"}
    original = IncidenciaCreate.model_validate(base)
    fakes.repository.find_by_operation.return_value = stored_from(original)
    replay = {
        "null": {**base, "observacion": None},
        "missing": base,
        "empty": {**base, "observacion": ""},
    }[omitted]
    assert (
        fakes.service.registrar(USER, IncidenciaCreate.model_validate(replay))[1]
        is False
    )


def test_I16_la_clave_idempotente_incluye_al_conductor(fakes):
    other_conductor = uuid4()
    fakes.repository.conductor_id_for.return_value = other_conductor
    fakes.service.registrar(USER, payload())
    fakes.repository.find_by_operation.assert_called_once_with(
        other_conductor, OPERATION
    )
    assert fakes.repository.add.call_args.args[0].conductor_id == other_conductor


# --- I11: mismo identificador con otro contenido -----------------------------


@pytest.mark.parametrize(
    "changes",
    [
        {"tipo": "TRAFICO"},
        {"severidad": "BAJA"},
        {"ocurrida_en": "2026-10-27T09:14:59-05:00"},
        {"latitud": -12.0465},
        {"longitud": -77.0429},
        {"parada_id": str(STOP)},
        {"observacion": "Llanta pinchada: reporte de prueba "},
        {"observacion": "llanta pinchada: reporte de prueba"},
    ],
    ids=[
        "tipo",
        "severidad",
        "hora",
        "latitud",
        "longitud",
        "parada",
        "espacio-final",
        "mayusculas",
    ],
)
def test_I11_mismo_operation_id_otro_contenido_devuelve_409(fakes, changes):
    fakes.repository.find_by_operation.return_value = stored_from(payload())
    with pytest.raises(IncidenciaConflicto) as error:
        fakes.service.registrar(USER, payload(**changes))
    assert "Llanta" not in str(error.value)
    fakes.repository.add.assert_not_called()


# --- I05 / I14: tolerancia de hora -------------------------------------------


@pytest.mark.parametrize(
    "ocurrida_en,valid",
    [
        (T0, True),
        (T0 + OCURRIDA_MAX_FUTURO, True),
        (T0 + OCURRIDA_MAX_FUTURO + timedelta(seconds=1), False),
        (datetime(2020, 1, 1, tzinfo=timezone.utc), True),
    ],
    ids=["T0", "T0+5min", "T0+5min+1s", "pasada-sin-antiguedad-maxima"],
)
def test_I05_I14_tolerancia_futura_inclusiva_y_sin_antiguedad(
    fakes, ocurrida_en, valid
):
    data = payload(ocurrida_en=ocurrida_en.isoformat())
    if valid:
        assert fakes.service.registrar(USER, data)[1] is True
    else:
        with pytest.raises(IncidenciaInvalida):
            fakes.service.registrar(USER, data)
        fakes.repository.add.assert_not_called()


def test_I05_compara_instantes_en_utc():
    utc = payload(ocurrida_en="2026-10-27T14:15:00Z")
    assert utc.ocurrida_en == payload().ocurrida_en


# --- I07 / I10: parada y perfil ----------------------------------------------


def test_I07_parada_inexistente_devuelve_422_generico(fakes):
    fakes.repository.stop_owner.return_value = None
    with pytest.raises(IncidenciaInvalida):
        fakes.service.registrar(USER, payload(parada_id=str(STOP)))
    fakes.repository.add.assert_not_called()


def test_I10_parada_de_otro_conductor_devuelve_403_generico(fakes):
    fakes.repository.stop_owner.return_value = uuid4()
    with pytest.raises(IncidenciaParadaAjena):
        fakes.service.registrar(USER, payload(parada_id=str(STOP)))
    fakes.repository.add.assert_not_called()


def test_I10_conductor_sin_perfil_vinculado_devuelve_403(fakes):
    fakes.repository.conductor_id_for.return_value = None
    with pytest.raises(IncidenciaSinConductor):
        fakes.service.registrar(USER, payload())
    fakes.repository.find_by_operation.assert_not_called()


# --- I13: carrera concurrente ------------------------------------------------


@pytest.mark.parametrize("equivalent", [True, False])
def test_I13_carrera_relee_y_responde_200_o_409_nunca_5xx(fakes, equivalent):
    data = payload()
    fakes.repository.add.side_effect = IncidenciaDuplicateOperation()
    fakes.repository.find_by_operation.side_effect = [
        None,
        stored_from(data) if equivalent else stored_from(data, tipo="OTRO"),
    ]
    if equivalent:
        ack, created = fakes.service.registrar(USER, data)
        assert (ack.operation_id, created) == (OPERATION, False)
    else:
        with pytest.raises(IncidenciaConflicto):
            fakes.service.registrar(USER, data)


def test_I13_carrera_sin_registro_ganador_es_no_disponible(fakes):
    fakes.repository.add.side_effect = IncidenciaDuplicateOperation()
    fakes.repository.find_by_operation.side_effect = [None, None]
    with pytest.raises(IncidenciaUnavailable):
        fakes.service.registrar(USER, payload())


def test_I13_carrera_sin_perfil_en_la_relectura_es_no_disponible(fakes):
    fakes.repository.add.side_effect = IncidenciaDuplicateOperation()
    fakes.repository.conductor_id_for.side_effect = [CONDUCTOR, None]
    with pytest.raises(IncidenciaUnavailable):
        fakes.service.registrar(USER, payload())


def test_I13_carrera_con_fallo_de_almacenamiento_es_no_disponible(fakes):
    fakes.repository.add.side_effect = IncidenciaDuplicateOperation()
    fakes.repository.find_by_operation.side_effect = [
        None,
        IncidenciaStorageError("private"),
    ]
    with pytest.raises(IncidenciaUnavailable):
        fakes.service.registrar(USER, payload())


@pytest.mark.parametrize(
    "failure", [IncidenciaStorageError("private"), SQLAlchemyError("private")]
)
def test_fallos_de_almacenamiento_se_sanean(fakes, failure):
    fakes.repository.conductor_id_for.side_effect = failure
    with pytest.raises(IncidenciaUnavailable) as error:
        fakes.service.registrar(USER, payload())
    assert "private" not in str(error.value)


def test_el_reloj_del_servidor_por_defecto_es_utc():
    assert module.utc_now().utcoffset() == timedelta(0)


# --- Listado (I02) -----------------------------------------------------------


def test_I02_listado_en_hora_de_lima_sin_datos_personales(fakes):
    row = IncidenciaRow(
        uuid4(),
        "AVERIA",
        "ALTA",
        T0,
        T0 + timedelta(minutes=1),
        CONDUCTOR,
        "Conductora Demo Uno",
        -12.0464,
        -77.0428,
        "",
        "PENDIENTE_VALIDACION",
    )
    fakes.repository.list_page.return_value = ([row], 41)

    page = fakes.service.listar(EstadoIncidencia.PENDIENTE_VALIDACION, 3, 20)

    fakes.repository.list_page.assert_called_once_with("PENDIENTE_VALIDACION", 3, 20)
    assert (page.page, page.page_size, page.total) == (3, 20, 41)
    [item] = page.items
    assert item.ocurrida_en.utcoffset() == timedelta(hours=-5)
    assert item.observacion == ""
    assert item.conductor.model_dump() == {
        "conductor_id": CONDUCTOR,
        "nombre": "Conductora Demo Uno",
    }


def test_listado_con_fallo_de_almacenamiento_se_sanea(fakes):
    fakes.repository.list_page.side_effect = IncidenciaStorageError("private")
    with pytest.raises(IncidenciaUnavailable):
        fakes.service.listar(EstadoIncidencia.PENDIENTE_VALIDACION, 1, 20)


# --- Esquema: I04, I05, I06, I07, I14 ----------------------------------------


@pytest.mark.parametrize(
    "field", ["operation_id", "tipo", "severidad", "ocurrida_en", "latitud", "longitud"]
)
def test_I04_campo_obligatorio_ausente_o_null(field):
    missing = {key: value for key, value in FIXTURE.items() if key != field}
    with pytest.raises(ValidationError):
        IncidenciaCreate.model_validate_json(json.dumps(missing))
    with pytest.raises(ValidationError):
        IncidenciaCreate.model_validate_json(json.dumps({**FIXTURE, field: None}))


def test_I05_fecha_sin_zona_es_invalida():
    with pytest.raises(ValidationError):
        payload(ocurrida_en="2026-10-27T09:15:00")


@pytest.mark.parametrize("text", ["ñ" * (OBSERVACION_MAX + 1), "😀" * 501])
def test_I06_observacion_de_501_puntos_de_codigo_sin_truncar(text):
    with pytest.raises(ValidationError) as error:
        payload(observacion=text)
    assert text not in str(error.value)


@pytest.mark.parametrize(
    "changes",
    [
        {"tipo": "DESVIO"},
        {"tipo": ""},
        {"tipo": "averia"},
        {"severidad": "URGENTE"},
        {"severidad": ""},
        {"severidad": "alta"},
        {"latitud": 90.0001},
        {"latitud": -90.0001},
        {"longitud": 180.0001},
        {"longitud": -180.0001},
        {"latitud": True},
        {"longitud": False},
        {"latitud": "-12.0464"},
        {"longitud": "-77"},
        {"operation_id": "no-es-uuid"},
        {"operation_id": str(uuid1())},
        {"parada_id": "parada-123"},
        {"conductor_id": str(uuid4())},
        {"usuario_id": str(uuid4())},
        {"reportada_por": str(uuid4())},
        {"ruta_id": str(uuid4())},
        {"estado": "VALIDADA"},
    ],
)
def test_I07_variaciones_invalidas_rechazadas(changes):
    with pytest.raises(ValidationError):
        payload(**changes)


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity", "1e400"])
@pytest.mark.parametrize("field", ["latitud", "longitud"])
def test_I07_coordenadas_no_finitas(field, raw):
    document = json.dumps(FIXTURE).replace(
        f'"{field}": {FIXTURE[field]}', f'"{field}": {raw}'
    )
    with pytest.raises(ValidationError):
        IncidenciaCreate.model_validate_json(document)


def test_I14_limites_validos_y_observacion_normalizada():
    assert payload(observacion="😀" * OBSERVACION_MAX).observacion == "😀" * 500
    assert payload(observacion=None).observacion == ""
    assert payload(observacion="").observacion == ""
    assert payload(observacion="  con espacios  ").observacion == "  con espacios  "
    base = {key: value for key, value in FIXTURE.items() if key != "observacion"}
    assert IncidenciaCreate.model_validate(base).observacion == ""
    extremes = payload(latitud=90, longitud=-180)
    assert (extremes.latitud, extremes.longitud) == (90.0, -180.0)
    assert payload(latitud=-90, longitud=180).latitud == -90.0


@pytest.mark.parametrize("tipo", constants.TIPOS)
@pytest.mark.parametrize("severidad", constants.SEVERIDADES)
def test_I14_matriz_de_seis_tipos_por_tres_severidades(fakes, tipo, severidad):
    ack, created = fakes.service.registrar(
        USER, payload(tipo=tipo, severidad=severidad)
    )
    assert created and ack.estado is EstadoIncidencia.PENDIENTE_VALIDACION


def test_auditoria_de_incidencia_exige_actor_y_entidad():
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
