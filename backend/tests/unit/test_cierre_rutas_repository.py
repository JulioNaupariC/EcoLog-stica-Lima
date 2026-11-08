"""ECL-119: closure repository queries without a database (shape and errors)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.cierre_rutas import CierreRutaRepository, CierreStorageError

DESDE = datetime(2026, 11, 1, 5, tzinfo=timezone.utc)
HASTA = datetime(2026, 12, 1, 5, tzinfo=timezone.utc)


def sql(session) -> str:
    return str(session.execute.call_args.args[0].compile(dialect=postgresql.dialect()))


def test_writes_lock_the_route_and_the_stop():
    session = MagicMock()
    repository = CierreRutaRepository(session)
    session.execute.return_value.scalar_one_or_none.return_value = "ruta"
    assert repository.ruta(uuid4()) == "ruta"
    assert "FOR UPDATE" in sql(session)
    repository.parada(uuid4(), uuid4())
    consulta = sql(session)
    assert "FOR UPDATE" in consulta and "parada_ruta.ruta_id =" in consulta
    session.execute.return_value.all.return_value = [("ATENDIDA", 3), ("PENDIENTE", 1)]
    assert repository.conteo_paradas(uuid4()) == {"ATENDIDA": 3, "PENDIENTE": 1}
    repository.guardar()
    session.flush.assert_called_once()


def test_aggregate_queries_filter_closed_routes_by_closing_instant():
    session = MagicMock()
    repository = CierreRutaRepository(session)
    session.execute.return_value.mappings.return_value.one.return_value = {"rutas": 0}
    assert repository.totales(DESDE, HASTA) == {"rutas": 0}
    consulta = sql(session)
    assert "ruta.estado =" in consulta and "ruta.cerrada_en >=" in consulta
    assert "ruta.cerrada_en <" in consulta and "trazado" not in consulta
    session.execute.return_value.scalars.return_value = ["REF-A"]
    assert repository.versiones(DESDE, HASTA) == ["REF-A"]
    assert "DISTINCT" in sql(session)
    session.execute.return_value.one.return_value = (3, 4)
    assert repository.cumplimiento(DESDE, HASTA) == (3, 4)
    consulta = sql(session)
    assert "parada_ruta.atendida_en >= pedido.ventana_inicio" in consulta
    assert "FILTER" in consulta


def test_storage_errors_are_sanitized():
    session = MagicMock()
    session.execute.side_effect = SQLAlchemyError("private")
    session.flush.side_effect = SQLAlchemyError("private")
    repository = CierreRutaRepository(session)
    for llamada in (
        lambda: repository.ruta(uuid4()),
        lambda: repository.totales(DESDE, HASTA),
        repository.guardar,
    ):
        with pytest.raises(CierreStorageError) as error:
            llamada()
        assert "private" not in str(error.value)
