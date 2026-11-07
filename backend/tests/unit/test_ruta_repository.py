"""ECL-95: route repository and model metadata, without a database."""

from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core import rutas as catalogos
from app.models import Optimizacion, ParadaRuta, PedidoNoAsignado, Ruta
from app.repositories.rutas import JornadaParada, RutaRepository, RutaStorageError
from app.schemas import rutas as contrato


def test_catalogues_match_the_st045_contract():
    assert catalogos.ESTADOS_OPTIMIZACION == tuple(
        e.value for e in contrato.EstadoOptimizacion
    )
    assert catalogos.ESTADOS_RUTA == tuple(e.value for e in contrato.EstadoRuta)
    assert catalogos.ESTADOS_PARADA == tuple(e.value for e in contrato.EstadoParada)
    assert catalogos.MOTIVOS_SIN_CONDUCTOR == tuple(
        e.value for e in contrato.MotivoSinConductor
    )
    # The database admits JORNADA_INVIABLE ahead of the API (BDD decision 5).
    assert set(e.value for e in contrato.MotivoNoAsignado) < set(
        catalogos.MOTIVOS_NO_ASIGNADO
    )


def test_tables_and_key_constraints_are_declared():
    names = {
        constraint.name
        for model in (Optimizacion, Ruta, ParadaRuta, PedidoNoAsignado)
        for constraint in model.__table__.constraints
    }
    assert {
        "ck_optimizacion_parametros",
        "ck_optimizacion_finalizada",
        "ck_ruta_conductor",
        "uq_ruta_vehiculo",
        "uq_parada_ruta_pedido",
        "fk_parada_ruta_ruta",
        "ck_pedido_no_asignado_motivo",
    } <= names
    assert repr(Optimizacion()) == "<Optimizacion>"
    assert repr(Ruta()) == "<Ruta>"
    assert repr(ParadaRuta()) == "<ParadaRuta>"
    assert repr(PedidoNoAsignado()) == "<PedidoNoAsignado>"


def test_jornada_of_an_assignment_with_a_planned_stop():
    session = MagicMock()
    ruta_id, conductor_id = uuid4(), uuid4()
    session.execute.return_value.one_or_none.return_value = (
        ruta_id,
        conductor_id,
        date(2026, 11, 9),
    )
    assert RutaRepository(session).jornada_de_asignacion(uuid4()) == JornadaParada(
        ruta_id, conductor_id, date(2026, 11, 9)
    )
    sql = str(session.execute.call_args.args[0])
    assert "driver_stop_assignment.parada_ruta_id = parada_ruta.parada_id" in sql


def test_assignment_without_route_has_no_jornada():
    session = MagicMock()
    session.execute.return_value.one_or_none.return_value = None
    assert RutaRepository(session).jornada_de_asignacion(uuid4()) is None


def test_storage_errors_are_sanitized():
    session = MagicMock()
    session.execute.side_effect = SQLAlchemyError("private SQL")
    with pytest.raises(RutaStorageError, match="^Route storage unavailable$"):
        RutaRepository(session).jornada_de_asignacion(uuid4())
