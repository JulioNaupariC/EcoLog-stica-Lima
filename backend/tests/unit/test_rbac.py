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
