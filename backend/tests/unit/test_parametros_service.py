"""EN-008 (ECL-26): service and repository logic without a database.

PostgreSQL behaviour (constraints, locks, history) is covered by
``tests/integration/test_parametros.py``.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.parametro import Parametro, ParametroVersion
from app.repositories import parametros as repo_module
from app.repositories.parametros import (
    ParametroRepository,
    ParametroStorageError,
    ParametroVersionDuplicada,
)
from app.schemas.parametro import ValorParametro, VersionCreate
from app.services import parametros as module
from app.services.parametros import (
    ParametrosConflicto,
    ParametroService,
    ParametrosNoEncontrados,
    ParametrosUnavailable,
)

T0 = datetime(2026, 11, 1, 5, tzinfo=timezone.utc)
VALORES = [
    ValorParametro(
        codigo="PRECIO_COMBUSTIBLE_GALON",
        valor=Decimal("17.50"),
        unidad="PEN/gal",
        fuente="RN-011",
    ),
    ValorParametro(
        codigo="LITROS_POR_GALON",
        valor=Decimal("3.785411784"),
        unidad="L/gal",
        fuente="NIST HB44",
    ),
    ValorParametro(
        codigo="COSTO_MANTENIMIENTO_KM",
        valor=Decimal("1.20"),
        unidad="PEN/km",
        fuente="RN-012",
    ),
]


def nueva(desde=T0):
    return VersionCreate(version="V2", vigente_desde=desde, valores=VALORES)


def guardada(codigo="V1", desde=T0):
    return ParametroVersion(
        version_id=uuid4(), version=codigo, vigente_desde=desde, vigente_hasta=None
    )


@pytest.fixture
def mocks(monkeypatch):
    session = MagicMock()

    class Factory:
        def __call__(self):
            return contextmanager(lambda: (yield session))()

        def begin(self):
            return contextmanager(lambda: (yield session))()

    repository = MagicMock()
    # Like the real flush: the stored version gets its identifier.
    repository.agregar.side_effect = lambda version, _valores: setattr(
        version, "version_id", uuid4()
    )
    audit = MagicMock()
    monkeypatch.setattr(module, "ParametroRepository", lambda _s: repository)
    monkeypatch.setattr(module, "AuditoriaRepository", lambda _s: audit)
    return ParametroService(Factory()), repository, audit


def test_register_first_version_without_closing(mocks):
    service, repository, audit = mocks
    repository.abierta_para_cierre.return_value = None
    actor = uuid4()
    result = service.registrar(nueva(), actor)
    assert result.version == "V2" and len(result.valores) == 3
    repository.cerrar.assert_not_called()
    registro = audit.insert.call_args.args[0]
    assert registro.usuario_id == actor
    assert registro.detalle.cierra_version_anterior is False
    assert registro.detalle.codigos == tuple(sorted(v.codigo for v in VALORES))


def test_register_closes_the_open_version_at_the_new_start(mocks):
    service, repository, audit = mocks
    abierta = guardada()
    repository.abierta_para_cierre.return_value = abierta
    inicio = T0 + timedelta(days=7)
    service.registrar(nueva(inicio), uuid4())
    repository.cerrar.assert_called_once_with(abierta.version_id, inicio)
    assert audit.insert.call_args.args[0].detalle.cierra_version_anterior is True


@pytest.mark.parametrize("inicio", [T0, T0 - timedelta(days=1)])
def test_start_not_after_the_open_version_is_a_conflict(mocks, inicio):
    service, repository, audit = mocks
    repository.abierta_para_cierre.return_value = guardada()
    with pytest.raises(ParametrosConflicto):
        service.registrar(nueva(inicio), uuid4())
    repository.agregar.assert_not_called()
    audit.insert.assert_not_called()


def test_duplicate_code_is_a_conflict_and_storage_errors_are_sanitized(mocks):
    service, repository, _ = mocks
    repository.abierta_para_cierre.return_value = None
    repository.agregar.side_effect = ParametroVersionDuplicada()
    with pytest.raises(ParametrosConflicto):
        service.registrar(nueva(), uuid4())
    repository.agregar.side_effect = ParametroStorageError("private SQL")
    with pytest.raises(ParametrosUnavailable, match="^Parameter service unavailable$"):
        service.registrar(nueva(), uuid4())


def test_reads_and_reproducible_set(mocks):
    service, repository, _ = mocks
    version = guardada()
    repository.vigente_en.return_value = version
    repository.por_codigo.return_value = version
    repository.valores.return_value = [
        Parametro(codigo=v.codigo, valor=v.valor, unidad=v.unidad, fuente=v.fuente)
        for v in VALORES
    ]
    assert service.vigente(T0).version == "V1"
    repository.vigente_en.assert_called_once_with(T0)
    conjunto = service.conjunto("V1")
    assert conjunto.version == "V1"
    assert conjunto.valores["LITROS_POR_GALON"] == Decimal("3.785411784")
    service.vigente()  # now, in UTC
    assert repository.vigente_en.call_args.args[0].tzinfo is not None


def test_missing_versions_and_read_failures(mocks):
    service, repository, _ = mocks
    repository.vigente_en.return_value = None
    repository.por_codigo.return_value = None
    with pytest.raises(ParametrosNoEncontrados):
        service.vigente(T0)
    with pytest.raises(ParametrosNoEncontrados):
        service.por_version("X")
    repository.vigente_en.side_effect = ParametroStorageError()
    repository.por_codigo.side_effect = SQLAlchemyError("private")
    with pytest.raises(ParametrosUnavailable):
        service.vigente(T0)
    with pytest.raises(ParametrosUnavailable):
        service.por_version("X")


def test_repository_queries_and_insert():
    session = MagicMock()
    repository = ParametroRepository(session)
    session.scalar.return_value = "found"
    assert repository.vigente_en(T0) == "found"
    sql = str(session.scalar.call_args.args[0])
    assert "parametro_version.vigente_desde <=" in sql
    assert "vigente_hasta IS NULL" in sql
    assert repository.por_codigo("V1") == "found"
    assert repository.abierta_para_cierre() == "found"
    assert "FOR UPDATE" in str(
        session.scalar.call_args.args[0].compile(
            dialect=__import__(
                "sqlalchemy.dialects.postgresql", fromlist=["dialect"]
            ).dialect()
        )
    )
    session.scalars.return_value.all.return_value = ["a"]
    assert repository.valores(uuid4()) == ["a"]
    repository.cerrar(uuid4(), T0)
    version = guardada()
    valor = Parametro(codigo="LITROS_POR_GALON")
    repository.agregar(version, [valor])
    assert valor.version_id == version.version_id


def test_repository_errors_are_sanitized():
    session = MagicMock()
    session.scalar.side_effect = SQLAlchemyError("private")
    session.scalars.side_effect = SQLAlchemyError("private")
    session.execute.side_effect = SQLAlchemyError("private")
    repository = ParametroRepository(session)
    for call in (
        lambda: repository.vigente_en(T0),
        lambda: repository.por_codigo("V1"),
        lambda: repository.valores(uuid4()),
        lambda: repository.abierta_para_cierre(),
        lambda: repository.cerrar(uuid4(), T0),
    ):
        with pytest.raises(ParametroStorageError):
            call()


@pytest.mark.parametrize(
    "error,esperado",
    [
        (
            IntegrityError("x", {}, Exception("uq_parametro_version_codigo")),
            ParametroVersionDuplicada,
        ),
        (
            IntegrityError("x", {}, Exception("ck_parametro_valor")),
            ParametroStorageError,
        ),
        (SQLAlchemyError("private"), ParametroStorageError),
    ],
)
def test_insert_errors_are_classified(error, esperado):
    session = MagicMock()
    session.flush.side_effect = error
    with pytest.raises(esperado):
        ParametroRepository(session).agregar(guardada(), [])


def test_models_repr():
    assert repr(ParametroVersion()) == "<ParametroVersion>"
    assert repr(Parametro()) == "<Parametro>"
    assert repo_module.ParametroRepository is ParametroRepository
