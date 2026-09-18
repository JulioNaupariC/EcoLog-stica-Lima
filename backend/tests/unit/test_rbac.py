from dataclasses import replace
from uuid import uuid4

import pytest

from app.core.rbac import (
    MATRIZ_RBAC,
    Alcance,
    Contexto,
    Identidad,
    Motivo,
    Permiso,
    Rol,
    evaluar,
)
from app.models.usuario import ROLES


@pytest.fixture
def actor():
    return Identidad(uuid4(), Rol.OPERADOR, "ACTIVO")


def test_allowed_and_denied(actor):
    assert evaluar(actor, Permiso.OPTIMIZACIONES_EJECUTAR).permitido
    assert evaluar(actor, Permiso.USUARIOS_CREAR).motivo == Motivo.SIN_PERMISO
    assert not evaluar(
        replace(actor, rol=Rol.AUDITOR), Permiso.VEHICULOS_ACTUALIZAR
    ).permitido


@pytest.mark.parametrize("role", ["invalid", "operador", None, [], {}])
def test_invalid_role(actor, role):
    assert (
        evaluar(replace(actor, rol=role), Permiso.RUTAS_CONSULTAR).motivo
        == Motivo.ROL_INVALIDO
    )


@pytest.mark.parametrize("state", ["INACTIVO", "BLOQUEADO", "", None])
def test_non_active(actor, state):
    assert (
        evaluar(replace(actor, estado=state), Permiso.RUTAS_CONSULTAR).motivo
        == Motivo.ESTADO_NO_ACTIVO
    )


def test_invalid_identity_and_permission(actor):
    for identity in (None, {}, replace(actor, usuario_id="invalid")):
        assert (
            evaluar(identity, Permiso.RUTAS_CONSULTAR).motivo
            == Motivo.IDENTIDAD_INVALIDA
        )
    for permission in (None, [], "rutas.consultar", "secret"):
        assert evaluar(actor, permission).motivo == Motivo.PERMISO_INVALIDO


@pytest.mark.parametrize("context", [{}, [], "context", object()])
def test_invalid_context_denies_general_permission(actor, context):
    decision = evaluar(actor, Permiso.PARAMETROS_CONSULTAR, context)
    assert not decision.permitido
    assert decision.motivo is Motivo.CONTEXTO_INSUFICIENTE


def test_none_context_is_valid_for_general_permission(actor):
    decision = evaluar(actor, Permiso.PARAMETROS_CONSULTAR, None)
    assert decision.permitido
    assert decision.alcance is Alcance.GENERAL


def test_complete_rbac_matrix_matches_approved_grants():
    expected = {
        Rol.ADMINISTRADOR: {
            Permiso.USUARIOS_CREAR: Alcance.GENERAL,
            Permiso.USUARIOS_CONSULTAR: Alcance.GENERAL,
            Permiso.USUARIOS_ACTUALIZAR: Alcance.GENERAL,
            Permiso.USUARIOS_DESACTIVAR: Alcance.GENERAL,
            Permiso.PARAMETROS_CREAR: Alcance.GENERAL,
            Permiso.PARAMETROS_CONSULTAR: Alcance.GENERAL,
            Permiso.PARAMETROS_ACTUALIZAR: Alcance.GENERAL,
            Permiso.PARAMETROS_DESACTIVAR: Alcance.GENERAL,
            Permiso.VEHICULOS_CREAR: Alcance.GENERAL,
            Permiso.VEHICULOS_CONSULTAR: Alcance.GENERAL,
            Permiso.VEHICULOS_ACTUALIZAR: Alcance.GENERAL,
            Permiso.VEHICULOS_DESACTIVAR: Alcance.GENERAL,
            Permiso.CONDUCTORES_CREAR: Alcance.GENERAL,
            Permiso.CONDUCTORES_CONSULTAR: Alcance.GENERAL,
            Permiso.CONDUCTORES_ACTUALIZAR: Alcance.GENERAL,
            Permiso.CONDUCTORES_DESACTIVAR: Alcance.GENERAL,
            Permiso.PEDIDOS_CREAR: Alcance.GENERAL,
            Permiso.PEDIDOS_CONSULTAR: Alcance.GENERAL,
            Permiso.PEDIDOS_ACTUALIZAR: Alcance.GENERAL,
            Permiso.PEDIDOS_DESACTIVAR: Alcance.GENERAL,
            Permiso.CLIENTES_CREAR: Alcance.GENERAL,
            Permiso.CLIENTES_CONSULTAR: Alcance.GENERAL,
            Permiso.CLIENTES_ACTUALIZAR: Alcance.GENERAL,
            Permiso.CLIENTES_DESACTIVAR: Alcance.GENERAL,
            Permiso.OPTIMIZACIONES_CONSULTAR: Alcance.GENERAL,
            Permiso.RUTAS_CONSULTAR: Alcance.GENERAL,
            Permiso.INCIDENCIAS_CONSULTAR: Alcance.GENERAL,
            Permiso.INDICADORES_CONSULTAR: Alcance.GENERAL,
            Permiso.REPORTES_CONSULTAR: Alcance.GENERAL,
            Permiso.REPORTES_DESCARGAR: Alcance.GENERAL,
            Permiso.AUDITORIA_CONSULTAR: Alcance.GENERAL,
        },
        Rol.OPERADOR: {
            Permiso.USUARIOS_CONSULTAR: Alcance.GENERAL,
            Permiso.PARAMETROS_CONSULTAR: Alcance.GENERAL,
            Permiso.VEHICULOS_CREAR: Alcance.GENERAL,
            Permiso.VEHICULOS_CONSULTAR: Alcance.GENERAL,
            Permiso.VEHICULOS_ACTUALIZAR: Alcance.GENERAL,
            Permiso.CONDUCTORES_CREAR: Alcance.GENERAL,
            Permiso.CONDUCTORES_CONSULTAR: Alcance.GENERAL,
            Permiso.CONDUCTORES_ACTUALIZAR: Alcance.GENERAL,
            Permiso.PEDIDOS_CREAR: Alcance.GENERAL,
            Permiso.PEDIDOS_CONSULTAR: Alcance.GENERAL,
            Permiso.PEDIDOS_ACTUALIZAR: Alcance.GENERAL,
            Permiso.CLIENTES_CREAR: Alcance.GENERAL,
            Permiso.CLIENTES_CONSULTAR: Alcance.GENERAL,
            Permiso.CLIENTES_ACTUALIZAR: Alcance.GENERAL,
            Permiso.OPTIMIZACIONES_CONSULTAR: Alcance.GENERAL,
            Permiso.OPTIMIZACIONES_EJECUTAR: Alcance.GENERAL,
            Permiso.RUTAS_REOPTIMIZAR: Alcance.GENERAL,
            Permiso.RUTAS_CONSULTAR: Alcance.GENERAL,
            Permiso.RUTAS_ACTUALIZAR_ESTADO: Alcance.GENERAL,
            Permiso.INCIDENCIAS_CREAR: Alcance.GENERAL,
            Permiso.INCIDENCIAS_CONSULTAR: Alcance.GENERAL,
            Permiso.INCIDENCIAS_ACTUALIZAR: Alcance.GENERAL,
            Permiso.INDICADORES_CONSULTAR: Alcance.GENERAL,
            Permiso.REPORTES_CONSULTAR: Alcance.GENERAL,
            Permiso.REPORTES_DESCARGAR: Alcance.GENERAL,
            Permiso.AUDITORIA_CONSULTAR: Alcance.PROPIO,
        },
        Rol.CONDUCTOR: {
            Permiso.CONDUCTORES_CONSULTAR: Alcance.PROPIO,
            Permiso.INCIDENCIAS_CREAR: Alcance.PROPIO,
            Permiso.INCIDENCIAS_CONSULTAR: Alcance.PROPIO,
            Permiso.INDICADORES_CONSULTAR: Alcance.PROPIO,
            Permiso.REPORTES_CONSULTAR: Alcance.PROPIO,
            Permiso.REPORTES_DESCARGAR: Alcance.PROPIO,
            Permiso.AUDITORIA_CONSULTAR: Alcance.PROPIO,
            Permiso.VEHICULOS_CONSULTAR: Alcance.ASIGNADO_JORNADA,
            Permiso.PEDIDOS_CONSULTAR: Alcance.ASIGNADO_JORNADA,
            Permiso.CLIENTES_CONSULTAR: Alcance.ASIGNADO_JORNADA,
            Permiso.RUTAS_CONSULTAR: Alcance.ASIGNADO_JORNADA,
            Permiso.RUTAS_ACTUALIZAR_ESTADO: Alcance.ASIGNADO_JORNADA,
        },
        Rol.ANALISTA: {
            Permiso.PARAMETROS_CONSULTAR: Alcance.GENERAL,
            Permiso.OPTIMIZACIONES_CONSULTAR: Alcance.GENERAL,
            Permiso.INDICADORES_CONSULTAR: Alcance.GENERAL,
            Permiso.REPORTES_CONSULTAR: Alcance.GENERAL,
            Permiso.REPORTES_DESCARGAR: Alcance.GENERAL,
            Permiso.COMPENSACION_CONSULTAR: Alcance.GENERAL,
            Permiso.VEHICULOS_CONSULTAR: Alcance.AGREGADO,
            Permiso.CONDUCTORES_CONSULTAR: Alcance.AGREGADO,
            Permiso.PEDIDOS_CONSULTAR: Alcance.AGREGADO,
            Permiso.CLIENTES_CONSULTAR: Alcance.AGREGADO,
            Permiso.RUTAS_CONSULTAR: Alcance.AGREGADO,
            Permiso.INCIDENCIAS_CONSULTAR: Alcance.AGREGADO,
        },
        Rol.AUDITOR: {
            Permiso.USUARIOS_CONSULTAR: Alcance.ANONIMIZADO,
            Permiso.CONDUCTORES_CONSULTAR: Alcance.ANONIMIZADO,
            Permiso.PEDIDOS_CONSULTAR: Alcance.ANONIMIZADO,
            Permiso.CLIENTES_CONSULTAR: Alcance.ANONIMIZADO,
            Permiso.RUTAS_CONSULTAR: Alcance.ANONIMIZADO,
            Permiso.INCIDENCIAS_CONSULTAR: Alcance.ANONIMIZADO,
            Permiso.REPORTES_CONSULTAR: Alcance.ANONIMIZADO,
            Permiso.REPORTES_DESCARGAR: Alcance.ANONIMIZADO,
            Permiso.PARAMETROS_CONSULTAR: Alcance.GENERAL,
            Permiso.VEHICULOS_CONSULTAR: Alcance.GENERAL,
            Permiso.OPTIMIZACIONES_CONSULTAR: Alcance.GENERAL,
            Permiso.INDICADORES_CONSULTAR: Alcance.GENERAL,
            Permiso.AUDITORIA_CONSULTAR: Alcance.GENERAL,
        },
    }

    assert set(expected) == set(Rol)
    for role in Rol:
        assert dict(MATRIZ_RBAC[role]) == expected[role]
        actor = Identidad(uuid4(), role, "ACTIVO")
        for permission in Permiso:
            expected_scope = expected[role].get(permission)
            if expected_scope is Alcance.PROPIO:
                context = Contexto(propietario_id=actor.usuario_id)
            elif expected_scope is Alcance.ASIGNADO_JORNADA:
                day = uuid4()
                context = Contexto(
                    asignado_a=actor.usuario_id,
                    jornada_recurso=day,
                    jornada_actual=day,
                )
            elif expected_scope in (Alcance.AGREGADO, Alcance.ANONIMIZADO):
                context = Contexto(proyeccion=expected_scope)
            else:
                context = None
            decision = evaluar(actor, permission, context)
            assert MATRIZ_RBAC[role].get(permission) == expected_scope
            assert decision.permitido is (expected_scope is not None)
            assert decision.alcance is expected_scope


def test_incidencias_deactivation_is_intentionally_undefined():
    # The approved restrictive interpretation grants deactivation to neither role
    # until the requirements contradiction is resolved in a later change.
    assert "incidencias.desactivar" not in {permission.value for permission in Permiso}
    assert all(
        "incidencias.desactivar" not in {permission.value for permission in grants}
        for grants in MATRIZ_RBAC.values()
    )


def test_immutable_and_least_privilege(actor):
    assert ROLES == tuple(role.value for role in Rol)
    with pytest.raises(TypeError):
        MATRIZ_RBAC[Rol.OPERADOR] = {}
    with pytest.raises(TypeError):
        MATRIZ_RBAC[Rol.OPERADOR][Permiso.USUARIOS_CREAR] = Alcance.GENERAL
    for role in Rol:
        for permission in Permiso:
            if permission.value.endswith(".desactivar"):
                assert evaluar(replace(actor, rol=role), permission).permitido == (
                    role == Rol.ADMINISTRADOR
                )
    assert not evaluar(
        replace(actor, rol=Rol.ADMINISTRADOR), Permiso.OPTIMIZACIONES_EJECUTAR
    ).permitido
    assert not evaluar(
        replace(actor, rol=Rol.ANALISTA), Permiso.AUDITORIA_CONSULTAR
    ).permitido
    assert all(
        p.value.endswith((".consultar", ".descargar")) for p in MATRIZ_RBAC[Rol.AUDITOR]
    )


def test_own_scope(actor):
    permission = Permiso.AUDITORIA_CONSULTAR
    assert not evaluar(actor, permission).permitido
    assert not evaluar(actor, permission, Contexto(propietario_id=uuid4())).permitido
    assert evaluar(
        actor, permission, Contexto(propietario_id=actor.usuario_id)
    ).permitido


def test_assignment_and_day(actor):
    actor = replace(actor, rol=Rol.CONDUCTOR)
    day = uuid4()
    context = Contexto(
        asignado_a=actor.usuario_id, jornada_actual=day, jornada_recurso=day
    )
    assert evaluar(actor, Permiso.RUTAS_CONSULTAR, context).permitido
    for invalid in (
        None,
        {},
        replace(context, asignado_a=uuid4()),
        replace(context, jornada_actual=uuid4()),
        replace(context, jornada_actual=None, jornada_recurso=None),
    ):
        assert not evaluar(actor, Permiso.RUTAS_CONSULTAR, invalid).permitido


@pytest.mark.parametrize(
    "role,scope", [(Rol.ANALISTA, Alcance.AGREGADO), (Rol.AUDITOR, Alcance.ANONIMIZADO)]
)
def test_restricted_projection(actor, role, scope):
    actor = replace(actor, rol=role)
    assert not evaluar(actor, Permiso.CONDUCTORES_CONSULTAR).permitido
    assert not evaluar(
        actor, Permiso.CONDUCTORES_CONSULTAR, Contexto(proyeccion=Alcance.GENERAL)
    ).permitido
    decision = evaluar(actor, Permiso.CONDUCTORES_CONSULTAR, Contexto(proyeccion=scope))
    assert decision.permitido and decision.alcance is scope
