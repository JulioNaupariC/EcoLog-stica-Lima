"""Static authorization policy. Inputs must come from trusted server-side data."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from uuid import UUID


class Rol(str, Enum):
    ADMINISTRADOR = "ADMINISTRADOR"
    OPERADOR = "OPERADOR"
    CONDUCTOR = "CONDUCTOR"
    ANALISTA = "ANALISTA"
    AUDITOR = "AUDITOR"


class Permiso(str, Enum):
    USUARIOS_CREAR = "usuarios.crear"
    USUARIOS_CONSULTAR = "usuarios.consultar"
    USUARIOS_ACTUALIZAR = "usuarios.actualizar"
    USUARIOS_DESACTIVAR = "usuarios.desactivar"
    PARAMETROS_CREAR = "parametros.crear"
    PARAMETROS_CONSULTAR = "parametros.consultar"
    PARAMETROS_ACTUALIZAR = "parametros.actualizar"
    PARAMETROS_DESACTIVAR = "parametros.desactivar"
    VEHICULOS_CREAR = "vehiculos.crear"
    VEHICULOS_CONSULTAR = "vehiculos.consultar"
    VEHICULOS_ACTUALIZAR = "vehiculos.actualizar"
    VEHICULOS_DESACTIVAR = "vehiculos.desactivar"
    CONDUCTORES_CREAR = "conductores.crear"
    CONDUCTORES_CONSULTAR = "conductores.consultar"
    CONDUCTORES_ACTUALIZAR = "conductores.actualizar"
    CONDUCTORES_DESACTIVAR = "conductores.desactivar"
    PEDIDOS_CREAR = "pedidos.crear"
    PEDIDOS_CONSULTAR = "pedidos.consultar"
    PEDIDOS_ACTUALIZAR = "pedidos.actualizar"
    PEDIDOS_DESACTIVAR = "pedidos.desactivar"
    CLIENTES_CREAR = "clientes.crear"
    CLIENTES_CONSULTAR = "clientes.consultar"
    CLIENTES_ACTUALIZAR = "clientes.actualizar"
    CLIENTES_DESACTIVAR = "clientes.desactivar"
    OPTIMIZACIONES_CONSULTAR = "optimizaciones.consultar"
    OPTIMIZACIONES_EJECUTAR = "optimizaciones.ejecutar"
    RUTAS_REOPTIMIZAR = "rutas.reoptimizar"
    RUTAS_CONSULTAR = "rutas.consultar"
    RUTAS_ACTUALIZAR_ESTADO = "rutas.actualizar_estado"
    INCIDENCIAS_CREAR = "incidencias.crear"
    INCIDENCIAS_CONSULTAR = "incidencias.consultar"
    INCIDENCIAS_ACTUALIZAR = "incidencias.actualizar"
    INDICADORES_CONSULTAR = "indicadores.consultar"
    REPORTES_CONSULTAR = "reportes.consultar"
    REPORTES_DESCARGAR = "reportes.descargar"
    COMPENSACION_CONSULTAR = "compensacion.consultar"
    AUDITORIA_CONSULTAR = "auditoria.consultar"


class Alcance(str, Enum):
    GENERAL = "GENERAL"
    PROPIO = "PROPIO"
    ASIGNADO_JORNADA = "ASIGNADO_JORNADA"
    AGREGADO = "AGREGADO"
    ANONIMIZADO = "ANONIMIZADO"


def _grants(
    *groups: tuple[Alcance, tuple[Permiso, ...]],
) -> Mapping[Permiso, Alcance]:
    return MappingProxyType(
        {permission: scope for scope, items in groups for permission in items}
    )


# Explicit grants: no inheritance, wildcard, runtime mutation or implicit CRUD.
MATRIZ_RBAC = MappingProxyType(
    {
        Rol.ADMINISTRADOR: _grants(
            (
                Alcance.GENERAL,
                (
                    Permiso.USUARIOS_CREAR,
                    Permiso.USUARIOS_CONSULTAR,
                    Permiso.USUARIOS_ACTUALIZAR,
                    Permiso.USUARIOS_DESACTIVAR,
                    Permiso.PARAMETROS_CREAR,
                    Permiso.PARAMETROS_CONSULTAR,
                    Permiso.PARAMETROS_ACTUALIZAR,
                    Permiso.PARAMETROS_DESACTIVAR,
                    Permiso.VEHICULOS_CREAR,
                    Permiso.VEHICULOS_CONSULTAR,
                    Permiso.VEHICULOS_ACTUALIZAR,
                    Permiso.VEHICULOS_DESACTIVAR,
                    Permiso.CONDUCTORES_CREAR,
                    Permiso.CONDUCTORES_CONSULTAR,
                    Permiso.CONDUCTORES_ACTUALIZAR,
                    Permiso.CONDUCTORES_DESACTIVAR,
                    Permiso.PEDIDOS_CREAR,
                    Permiso.PEDIDOS_CONSULTAR,
                    Permiso.PEDIDOS_ACTUALIZAR,
                    Permiso.PEDIDOS_DESACTIVAR,
                    Permiso.CLIENTES_CREAR,
                    Permiso.CLIENTES_CONSULTAR,
                    Permiso.CLIENTES_ACTUALIZAR,
                    Permiso.CLIENTES_DESACTIVAR,
                    Permiso.OPTIMIZACIONES_CONSULTAR,
                    Permiso.RUTAS_CONSULTAR,
                    Permiso.INCIDENCIAS_CONSULTAR,
                    Permiso.INDICADORES_CONSULTAR,
                    Permiso.REPORTES_CONSULTAR,
                    Permiso.REPORTES_DESCARGAR,
                    Permiso.AUDITORIA_CONSULTAR,
                ),
            )
        ),
        Rol.OPERADOR: _grants(
            (
                Alcance.GENERAL,
                (
                    Permiso.USUARIOS_CONSULTAR,
                    Permiso.PARAMETROS_CONSULTAR,
                    Permiso.VEHICULOS_CREAR,
                    Permiso.VEHICULOS_CONSULTAR,
                    Permiso.VEHICULOS_ACTUALIZAR,
                    Permiso.CONDUCTORES_CREAR,
                    Permiso.CONDUCTORES_CONSULTAR,
                    Permiso.CONDUCTORES_ACTUALIZAR,
                    Permiso.PEDIDOS_CREAR,
                    Permiso.PEDIDOS_CONSULTAR,
                    Permiso.PEDIDOS_ACTUALIZAR,
                    Permiso.CLIENTES_CREAR,
                    Permiso.CLIENTES_CONSULTAR,
                    Permiso.CLIENTES_ACTUALIZAR,
                    Permiso.OPTIMIZACIONES_CONSULTAR,
                    Permiso.OPTIMIZACIONES_EJECUTAR,
                    Permiso.RUTAS_REOPTIMIZAR,
                    Permiso.RUTAS_CONSULTAR,
                    Permiso.RUTAS_ACTUALIZAR_ESTADO,
                    Permiso.INCIDENCIAS_CREAR,
                    Permiso.INCIDENCIAS_CONSULTAR,
                    Permiso.INCIDENCIAS_ACTUALIZAR,
                    Permiso.INDICADORES_CONSULTAR,
                    Permiso.REPORTES_CONSULTAR,
                    Permiso.REPORTES_DESCARGAR,
                ),
            ),
            (Alcance.PROPIO, (Permiso.AUDITORIA_CONSULTAR,)),
        ),
        Rol.CONDUCTOR: _grants(
            (
                Alcance.PROPIO,
                (
                    Permiso.CONDUCTORES_CONSULTAR,
                    Permiso.INCIDENCIAS_CREAR,
                    Permiso.INCIDENCIAS_CONSULTAR,
                    Permiso.INDICADORES_CONSULTAR,
                    Permiso.REPORTES_CONSULTAR,
                    Permiso.REPORTES_DESCARGAR,
                    Permiso.AUDITORIA_CONSULTAR,
                ),
            ),
            (
                Alcance.ASIGNADO_JORNADA,
                (
                    Permiso.VEHICULOS_CONSULTAR,
                    Permiso.PEDIDOS_CONSULTAR,
                    Permiso.CLIENTES_CONSULTAR,
                    Permiso.RUTAS_CONSULTAR,
                    Permiso.RUTAS_ACTUALIZAR_ESTADO,
                ),
            ),
        ),
        Rol.ANALISTA: _grants(
            (
                Alcance.GENERAL,
                (
                    Permiso.PARAMETROS_CONSULTAR,
                    Permiso.OPTIMIZACIONES_CONSULTAR,
                    Permiso.INDICADORES_CONSULTAR,
                    Permiso.REPORTES_CONSULTAR,
                    Permiso.REPORTES_DESCARGAR,
                    Permiso.COMPENSACION_CONSULTAR,
                ),
            ),
            (
                Alcance.AGREGADO,
                (
                    Permiso.VEHICULOS_CONSULTAR,
                    Permiso.CONDUCTORES_CONSULTAR,
                    Permiso.PEDIDOS_CONSULTAR,
                    Permiso.CLIENTES_CONSULTAR,
                    Permiso.RUTAS_CONSULTAR,
                    Permiso.INCIDENCIAS_CONSULTAR,
                ),
            ),
        ),
        Rol.AUDITOR: _grants(
            (
                Alcance.ANONIMIZADO,
                (
                    Permiso.USUARIOS_CONSULTAR,
                    Permiso.CONDUCTORES_CONSULTAR,
                    Permiso.PEDIDOS_CONSULTAR,
                    Permiso.CLIENTES_CONSULTAR,
                    Permiso.RUTAS_CONSULTAR,
                    Permiso.INCIDENCIAS_CONSULTAR,
                    Permiso.REPORTES_CONSULTAR,
                    Permiso.REPORTES_DESCARGAR,
                ),
            ),
            (
                Alcance.GENERAL,
                (
                    Permiso.PARAMETROS_CONSULTAR,
                    Permiso.VEHICULOS_CONSULTAR,
                    Permiso.OPTIMIZACIONES_CONSULTAR,
                    Permiso.INDICADORES_CONSULTAR,
                    Permiso.AUDITORIA_CONSULTAR,
                ),
            ),
        ),
    }
)


class Motivo(str, Enum):
    PERMITIDO = "PERMITIDO"
    IDENTIDAD_INVALIDA = "IDENTIDAD_INVALIDA"
    ROL_INVALIDO = "ROL_INVALIDO"
    ESTADO_NO_ACTIVO = "ESTADO_NO_ACTIVO"
    PERMISO_INVALIDO = "PERMISO_INVALIDO"
    SIN_PERMISO = "SIN_PERMISO"
    CONTEXTO_INSUFICIENTE = "CONTEXTO_INSUFICIENTE"


@dataclass(frozen=True, repr=False)
class Identidad:
    """Verified, persisted actor supplied by the caller, never by request payload."""

    usuario_id: UUID
    rol: str
    estado: str


@dataclass(frozen=True, repr=False)
class Contexto:
    """Trusted resource facts and explicitly selected safe data projection."""

    propietario_id: UUID | None = None
    asignado_a: UUID | None = None
    jornada_recurso: UUID | None = None
    jornada_actual: UUID | None = None
    proyeccion: Alcance | None = None


@dataclass(frozen=True)
class Decision:
    permitido: bool
    motivo: Motivo
    alcance: Alcance | None = None


def evaluar(
    identidad: Identidad | None,
    permiso: Permiso,
    contexto: Contexto | None = None,
) -> Decision:
    """Deny unknown inputs and missing scope facts; performs no I/O."""
    if not isinstance(identidad, Identidad) or not isinstance(
        identidad.usuario_id, UUID
    ):
        return Decision(False, Motivo.IDENTIDAD_INVALIDA)
    try:
        rol = Rol(identidad.rol)
    except (ValueError, TypeError):
        return Decision(False, Motivo.ROL_INVALIDO)
    if identidad.estado != "ACTIVO":
        return Decision(False, Motivo.ESTADO_NO_ACTIVO)
    if not isinstance(permiso, Permiso):
        return Decision(False, Motivo.PERMISO_INVALIDO)
    alcance = MATRIZ_RBAC[rol].get(permiso)
    if alcance is None:
        return Decision(False, Motivo.SIN_PERMISO)
    contexto = contexto if isinstance(contexto, Contexto) else Contexto()
    if alcance == Alcance.PROPIO:
        valido = contexto.propietario_id == identidad.usuario_id
    elif alcance == Alcance.ASIGNADO_JORNADA:
        valido = (
            contexto.asignado_a == identidad.usuario_id
            and isinstance(contexto.jornada_actual, UUID)
            and contexto.jornada_actual == contexto.jornada_recurso
        )
    elif alcance in (Alcance.AGREGADO, Alcance.ANONIMIZADO):
        valido = contexto.proyeccion is alcance
    else:
        valido = True
    if not valido:
        return Decision(False, Motivo.CONTEXTO_INSUFICIENTE)
    return Decision(True, Motivo.PERMITIDO, alcance)
