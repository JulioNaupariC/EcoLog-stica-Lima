"""EN-008 (ECL-26) over PostgreSQL: versioned parameters (RNF-011).

A new version closes the open one without editing or deleting, the version
in force at any instant is unique, values keep their unit and source, an
optimization can only reference an existing version, every registration is
audited, and migration 0017 refuses to drop history. Data is synthetic.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from alembic import command
from app.core.parametros import REFERENCIA_INICIAL, UNIDADES
from app.db.session import session_factory
from app.models import Auditoria, Optimizacion, Parametro, ParametroVersion
from app.repositories.usuarios import UsuarioRepository
from app.schemas.parametro import ValorParametro, VersionCreate
from app.services.credenciales import CredentialService
from app.services.parametros import (
    ParametrosConflicto,
    ParametroService,
    ParametrosNoEncontrados,
)

pytestmark = pytest.mark.integration

T0 = datetime(2026, 11, 1, 5, 0, tzinfo=timezone.utc)  # 00:00 in Lima


@pytest.fixture
def parametros_database(migration_database):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    with factory.begin() as session:
        admin = (
            CredentialService(UsuarioRepository(session))
            .create("admin-parametros@example.test", "synthetic-1", "ADMINISTRADOR")
            .usuario_id
        )
    try:
        yield factory, config, admin
    finally:
        with factory.begin() as session:
            session.execute(delete(Optimizacion))
            session.execute(delete(Parametro))
            session.execute(delete(ParametroVersion))
            session.execute(delete(Auditoria))


def version(codigo, desde, precio="17.50"):
    valores = {v.codigo: v for v in REFERENCIA_INICIAL}
    return VersionCreate(
        version=codigo,
        vigente_desde=desde,
        valores=[
            ValorParametro(
                codigo=c,
                valor=Decimal(precio) if c == "PRECIO_COMBUSTIBLE_GALON" else v.valor,
                unidad=UNIDADES[c],
                fuente=v.fuente,
            )
            for c, v in valores.items()
        ],
    )


def test_new_version_closes_the_previous_and_history_is_kept(parametros_database):
    factory, _, admin = parametros_database
    service = ParametroService(factory)
    service.registrar(version("V1", T0), admin)
    segunda = service.registrar(version("V2", T0 + timedelta(days=7), "18.10"), admin)
    assert segunda.vigente_hasta is None
    primera = service.por_version("V1")
    assert primera.vigente_hasta == T0 + timedelta(days=7)
    # Version in force at each instant: [desde, hasta).
    assert service.vigente(T0 + timedelta(days=3)).version == "V1"
    assert service.vigente(T0 + timedelta(days=7)).version == "V2"
    with pytest.raises(ParametrosNoEncontrados):
        service.vigente(T0 - timedelta(seconds=1))
    conjunto = service.conjunto("V1")
    assert conjunto.valores["PRECIO_COMBUSTIBLE_GALON"] == Decimal("17.50")
    assert conjunto.valores["LITROS_POR_GALON"] == Decimal("3.785411784")
    assert service.conjunto("V2").valores["PRECIO_COMBUSTIBLE_GALON"] == Decimal(
        "18.10"
    )
    with factory() as session:
        acciones = session.scalars(
            select(Auditoria).where(Auditoria.accion == "PARAMETROS_VERSIONADOS")
        ).all()
        assert [a.detalle["cierra_version_anterior"] for a in acciones] == [
            False,
            True,
        ]
        assert all(a.entidad == "parametro" for a in acciones)
        assert "17.50" not in str([a.detalle for a in acciones])


def test_a_start_not_after_the_open_version_is_a_conflict(parametros_database):
    factory, _, admin = parametros_database
    service = ParametroService(factory)
    service.registrar(version("V1", T0), admin)
    with pytest.raises(ParametrosConflicto):
        service.registrar(version("V2", T0), admin)
    with pytest.raises(ParametrosConflicto):
        service.registrar(version("V1", T0 + timedelta(days=1)), admin)
    # Nothing half-written: still one open version, no extra audit.
    with factory() as session:
        assert session.scalar(text("SELECT count(*) FROM parametro_version")) == 1
        assert session.scalar(text("SELECT count(*) FROM auditoria")) == 1


@pytest.mark.parametrize(
    "sql,restriccion",
    [
        (
            "INSERT INTO parametro (version_id, codigo, valor, unidad, fuente) "
            "VALUES (:v, 'LITROS_POR_GALON', 3.78, 'L', 'x')",
            "ck_parametro_unidad",
        ),
        (
            "INSERT INTO parametro (version_id, codigo, valor, unidad, fuente) "
            "VALUES (:v, 'FACTOR_X', 1, 'L/gal', 'x')",
            "ck_parametro_codigo",
        ),
        (
            "INSERT INTO parametro (version_id, codigo, valor, unidad, fuente) "
            "VALUES (:v, 'CAPTURA_CO2_ARBOL_ANIO', 0, 'kgCO2/arbol/anio', 'x')",
            "ck_parametro_valor",
        ),
        (
            "INSERT INTO parametro (version_id, codigo, valor, unidad, fuente) "
            "VALUES (:v, 'CAPTURA_CO2_ARBOL_ANIO', 20, 'kgCO2/arbol/anio', '  ')",
            "ck_parametro_fuente",
        ),
        (
            "INSERT INTO parametro (version_id, codigo, valor, unidad, fuente) "
            "VALUES (:v, 'LITROS_POR_GALON', 3.78, 'L/gal', 'x')",
            "uq_parametro_version_codigo_valor",
        ),
    ],
)
def test_database_protects_units_codes_values_and_sources(
    parametros_database, sql, restriccion
):
    factory, _, admin = parametros_database
    ParametroService(factory).registrar(version("V1", T0), admin)
    with factory() as session:
        version_id = session.scalar(select(ParametroVersion.version_id))
    with pytest.raises(IntegrityError, match=restriccion), factory.begin() as session:
        session.execute(text(sql), {"v": version_id})


def test_only_one_open_version(parametros_database):
    factory, _, admin = parametros_database
    ParametroService(factory).registrar(version("V1", T0), admin)
    with (
        pytest.raises(IntegrityError, match="uq_parametro_version_abierta"),
        factory.begin() as session,
    ):
        session.add(
            ParametroVersion(
                version="V2", vigente_desde=T0 + timedelta(days=1), creada_por=admin
            )
        )


def test_optimizations_reference_an_existing_version(parametros_database):
    factory, _, admin = parametros_database
    ParametroService(factory).registrar(version("V1", T0), admin)

    def corrida(codigo):
        return Optimizacion(
            solicitada_por=admin,
            fecha_operacion=date(2026, 11, 9),
            estado="COMPLETADA",
            solicitada_en=T0 + timedelta(days=8),
            finalizada_en=T0 + timedelta(days=8, seconds=20),
            parametros_version=codigo,
        )

    with factory.begin() as session:
        session.add(corrida("V1"))
    with (
        pytest.raises(IntegrityError, match="fk_optimizacion_parametros"),
        factory.begin() as session,
    ):
        session.add(corrida("NO-EXISTE"))


def test_downgrade_refuses_with_parameter_history(parametros_database):
    factory, config, admin = parametros_database
    command.downgrade(config, "0016_modelo_rutas")
    command.upgrade(config, "head")
    ParametroService(factory).registrar(version("V1", T0), admin)
    with pytest.raises(DBAPIError, match="EN-008 parameter versions"):
        command.downgrade(config, "0016_modelo_rutas")
    with factory() as session:
        assert session.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0017_parametros_versionados"
        )
