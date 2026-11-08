"""ST-047 (ECL-96): optimization repository without a database.

Checks the shape of each query and that storage errors are sanitized; the
PostGIS results are covered by tests/integration/test_optimizaciones.py.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from app.models import Optimizacion, ParadaRuta, PedidoNoAsignado, Ruta
from app.repositories.optimizaciones import (
    ConductorElegible,
    OptimizacionRepository,
    OptimizacionStorageError,
    a_float,
    minutos_desde_medianoche,
)

T0 = datetime(2026, 11, 9, 5, 0, tzinfo=timezone.utc)


def sql(statement) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}
        )
    )


def ultimo(session) -> str:
    return sql(session.execute.call_args.args[0])


def test_helpers():
    assert minutos_desde_medianoche(T0 + timedelta(hours=9, minutes=30), T0) == 570
    assert minutos_desde_medianoche(T0 + timedelta(days=1, minutes=1), T0) == 1441
    assert a_float(None) == 0.0 and a_float(Decimal("1.5")) == 1.5


def test_selection_queries():
    session = MagicMock()
    session.execute.return_value.mappings.return_value = [{"pedido_id": 1}]
    repository = OptimizacionRepository(session)
    assert repository.pedidos_por_id([uuid4()]) == [{"pedido_id": 1}]
    consulta = ultimo(session)
    assert "ST_Y" in consulta and "pedido.pedido_id IN" in consulta
    repository.pedidos_pendientes(T0, T0 + timedelta(days=1), 151)
    consulta = ultimo(session)
    assert "pedido.estado =" in consulta and "LIMIT" in consulta
    assert "pedido.ventana_inicio >=" in consulta

    session.scalars.return_value.all.return_value = ["v"]
    assert repository.vehiculos(None, 16) == ["v"]
    assert "vehiculo.estado =" in sql(session.scalars.call_args.args[0])
    repository.vehiculos([uuid4()], 16)
    explicita = sql(session.scalars.call_args.args[0])
    assert "vehiculo.vehiculo_id IN" in explicita and "LIMIT" not in explicita

    conductor = {
        "conductor_id": uuid4(),
        "disponible_desde": T0,
        "disponible_hasta": T0 + timedelta(hours=8),
        "licencia_vigente_hasta": date(2026, 11, 9),
    }
    session.execute.return_value.mappings.return_value = [conductor]
    assert repository.conductores_candidatos() == [ConductorElegible(**conductor)]
    consulta = ultimo(session)
    assert (
        "usuario.rol =" in consulta and "conductor.licencia_vigente_hasta" in consulta
    )
    assert "licencia_vigente_hasta >=" not in consulta
    assert "dni" not in consulta.split("FROM")[0]


def test_writes():
    session = MagicMock()
    repository = OptimizacionRepository(session)
    corrida = Optimizacion()
    repository.crear(corrida)
    session.add.assert_called_with(corrida)

    run_id = uuid4()
    ruta = Ruta(ruta_id=uuid4())
    parada = ParadaRuta(pedido_id=uuid4(), secuencia=1)
    omitido = PedidoNoAsignado(pedido_id=uuid4())
    repository.completar(
        run_id, {"estado": "COMPLETADA"}, [(ruta, [parada])], [omitido]
    )
    assert parada.ruta_id == ruta.ruta_id and parada.optimizacion_id == run_id
    assert "optimizacion.estado =" in ultimo(session)
    session.add_all.assert_any_call([omitido])

    repository.fallar(run_id, "error seguro", T0)
    assert "UPDATE optimizacion" in ultimo(session)


def test_reads():
    session = MagicMock()
    repository = OptimizacionRepository(session)
    session.get.return_value = "run"
    assert repository.obtener(uuid4()) == "run"
    session.execute.return_value.mappings.return_value = []
    repository.rutas_de(uuid4())
    consulta = ultimo(session)
    assert "ST_AsGeoJSON" in consulta and "LEFT OUTER JOIN conductor" in consulta
    assert "conductor.dni" not in consulta and "telefono" not in consulta
    repository.paradas_de(uuid4())
    assert "ORDER BY parada_ruta.ruta_id, parada_ruta.secuencia" in ultimo(session)
    repository.no_asignados_de(uuid4())
    assert "pedido_no_asignado" in ultimo(session)

    session.scalar.return_value = 3
    session.scalars.return_value.all.return_value = ["a", "b"]
    assert repository.pagina(date(2026, 11, 9), 2, 2) == (["a", "b"], 3)
    pagina = sql(session.scalars.call_args.args[0])
    assert (
        "ORDER BY optimizacion.solicitada_en DESC, optimizacion.optimizacion_id"
        in pagina
    )
    assert "OFFSET" in pagina and "optimizacion.fecha_operacion =" in pagina
    session.scalar.return_value = None
    assert repository.pagina(None, 1, 20) == (["a", "b"], 0)


def test_aggregates():
    session = MagicMock()
    repository = OptimizacionRepository(session)
    assert repository.totales([]) == {} and repository.conteos([]) == {}
    a, b = uuid4(), uuid4()
    session.execute.return_value.mappings.return_value = [
        {"optimizacion_id": a, "rutas": 2}
    ]
    assert repository.totales([a, b]) == {a: {"optimizacion_id": a, "rutas": 2}}
    assert "GROUP BY ruta.optimizacion_id" in ultimo(session)
    session.execute.return_value.mappings.side_effect = [
        [{"optimizacion_id": a, "n": 5}],
        [{"optimizacion_id": b, "n": 1}],
    ]
    assert repository.conteos([a, b]) == {a: (5, 0), b: (0, 1)}


def test_storage_errors_are_sanitized():
    session = MagicMock()
    session.execute.side_effect = SQLAlchemyError("private")
    session.scalars.side_effect = SQLAlchemyError("private")
    session.scalar.side_effect = SQLAlchemyError("private")
    session.get.side_effect = SQLAlchemyError("private")
    session.flush.side_effect = SQLAlchemyError("private")
    repository = OptimizacionRepository(session)
    for call in (
        lambda: repository.pedidos_por_id([uuid4()]),
        lambda: repository.vehiculos(None, 1),
        lambda: repository.crear(Optimizacion()),
        lambda: repository.completar(uuid4(), {}, [], []),
        lambda: repository.fallar(uuid4(), "x", T0),
        lambda: repository.obtener(uuid4()),
        lambda: repository.pagina(None, 1, 1),
    ):
        with pytest.raises(OptimizacionStorageError, match="unavailable") as error:
            call()
        assert "private" not in str(error.value)
