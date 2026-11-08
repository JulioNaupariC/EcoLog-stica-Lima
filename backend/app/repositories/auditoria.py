"""Typed audit insertion; callers own transactions. No update/delete API."""

from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.incidencias import SeveridadIncidencia, TipoIncidencia
from app.core.rbac import Motivo, Permiso
from app.models.auditoria import Auditoria


class Evento(str, Enum):
    PERMITIDA = "AUTORIZACION_PERMITIDA"
    DENEGADA = "AUTORIZACION_DENEGADA"
    LOGIN_EXITOSO = "LOGIN_EXITOSO"
    LOGIN_FALLIDO = "LOGIN_FALLIDO"
    CUENTA_BLOQUEADA = "CUENTA_BLOQUEADA"
    SESION_CERRADA = "SESION_CERRADA"
    SESION_EXTENDIDA = "SESION_EXTENDIDA"
    VEHICULO_PARAMETROS_ACTUALIZADOS = "VEHICULO_PARAMETROS_ACTUALIZADOS"
    VEHICULO_DESACTIVADO = "VEHICULO_DESACTIVADO"
    CONDUCTOR_REGISTRADO = "CONDUCTOR_REGISTRADO"
    CONDUCTOR_ACTUALIZADO = "CONDUCTOR_ACTUALIZADO"
    CONTRASENA_RESTABLECIDA = "CONTRASENA_RESTABLECIDA"
    CONTRASENA_CAMBIADA = "CONTRASENA_CAMBIADA"
    INCIDENCIA_REGISTRADA = "INCIDENCIA_REGISTRADA"
    INCIDENCIA_RESUELTA = "INCIDENCIA_RESUELTA"
    PARAMETROS_VERSIONADOS = "PARAMETROS_VERSIONADOS"


class ResultadoAcceso(str, Enum):
    EXITOSO = "EXITOSO"
    CREDENCIALES_INVALIDAS = "CREDENCIALES_INVALIDAS"
    LIMITE_INTENTOS = "LIMITE_INTENTOS"
    CIERRE = "CIERRE"
    RENOVACION = "RENOVACION"


class Detalle(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )
    permiso: Permiso | None
    motivo: Motivo


class DetalleAcceso(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )
    resultado: ResultadoAcceso


CampoParametroVehiculo = Literal["rendimiento_km_l", "factor_co2_kg_km"]


class DetalleParametrosVehiculo(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )
    campos_modificados: tuple[CampoParametroVehiculo, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def campos_unicos(self) -> "DetalleParametrosVehiculo":
        if len(set(self.campos_modificados)) != len(self.campos_modificados):
            raise ValueError("Duplicate audit field")
        return self


class DetalleVehiculoDesactivado(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )


# Field names only: personal values (DNI, phone, name) are never audited.
CampoConductor = Literal[
    "nombre",
    "dni",
    "licencia_numero",
    "licencia_vigente_hasta",
    "experiencia_anios",
    "telefono",
    "punto_partida",
    "disponible_desde",
    "disponible_hasta",
]


class DetalleConductorRegistrado(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )


class DetalleConductorActualizado(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )
    campos_modificados: tuple[CampoConductor, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def campos_unicos(self) -> "DetalleConductorActualizado":
        if len(set(self.campos_modificados)) != len(self.campos_modificados):
            raise ValueError("Duplicate audit field")
        return self


# ECL-77: only how many sessions were revoked; never a password or its hash.
class DetalleContrasena(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )
    sesiones_revocadas: int = Field(ge=0)


# ECL-73 / RN-015: catalogue values and flags only; no location, note or person.
class DetalleIncidenciaRegistrada(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )
    tipo: TipoIncidencia
    severidad: SeveridadIncidencia
    con_parada: bool
    con_observacion: bool


class DetalleIncidenciaResuelta(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )
    estado: Literal["VALIDADA", "DESCARTADA"]
    con_motivo: bool


CodigoParametro = Literal[
    "PRECIO_COMBUSTIBLE_GALON",
    "LITROS_POR_GALON",
    "COSTO_MANTENIMIENTO_KM",
    "CAPTURA_CO2_ARBOL_ANIO",
]


class DetalleParametrosVersionados(BaseModel):
    """EN-008: which codes a new version sets; values live in ``parametro``."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )
    codigos: tuple[CodigoParametro, ...] = Field(min_length=1)
    cierra_version_anterior: bool

    @model_validator(mode="after")
    def codigos_unicos(self) -> "DetalleParametrosVersionados":
        if len(set(self.codigos)) != len(self.codigos):
            raise ValueError("Duplicate audit field")
        return self


class Registro(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )
    usuario_id: UUID | None
    entidad_id: UUID | None = None
    evento: Evento
    detalle: (
        Detalle
        | DetalleAcceso
        | DetalleParametrosVehiculo
        | DetalleVehiculoDesactivado
        | DetalleConductorRegistrado
        | DetalleConductorActualizado
        | DetalleContrasena
        | DetalleIncidenciaRegistrada
        | DetalleIncidenciaResuelta
        | DetalleParametrosVersionados
    )

    @model_validator(mode="after")
    def coherente(self) -> "Registro":
        authorization = self.evento in (Evento.PERMITIDA, Evento.DENEGADA)
        access = self.evento in (
            Evento.LOGIN_EXITOSO,
            Evento.LOGIN_FALLIDO,
            Evento.CUENTA_BLOQUEADA,
            Evento.SESION_CERRADA,
            Evento.SESION_EXTENDIDA,
        )
        parameter_update = self.evento is Evento.VEHICULO_PARAMETROS_ACTUALIZADOS
        deactivation = self.evento is Evento.VEHICULO_DESACTIVADO
        driver_created = self.evento is Evento.CONDUCTOR_REGISTRADO
        driver_updated = self.evento is Evento.CONDUCTOR_ACTUALIZADO
        password = self.evento in (
            Evento.CONTRASENA_RESTABLECIDA,
            Evento.CONTRASENA_CAMBIADA,
        )
        incident = self.evento is Evento.INCIDENCIA_REGISTRADA
        resolution = self.evento is Evento.INCIDENCIA_RESUELTA
        versioned = self.evento is Evento.PARAMETROS_VERSIONADOS
        if versioned != isinstance(self.detalle, DetalleParametrosVersionados):
            raise ValueError("Invalid audit event")
        if versioned and (self.usuario_id is None or self.entidad_id is None):
            raise ValueError("Invalid parameter audit event")
        if resolution != isinstance(self.detalle, DetalleIncidenciaResuelta):
            raise ValueError("Invalid audit event")
        if authorization != isinstance(self.detalle, Detalle):
            raise ValueError("Invalid audit event")
        if access != isinstance(self.detalle, DetalleAcceso):
            raise ValueError("Invalid audit event")
        if parameter_update != isinstance(self.detalle, DetalleParametrosVehiculo):
            raise ValueError("Invalid audit event")
        if deactivation != isinstance(self.detalle, DetalleVehiculoDesactivado):
            raise ValueError("Invalid audit event")
        if driver_created != isinstance(self.detalle, DetalleConductorRegistrado):
            raise ValueError("Invalid audit event")
        if driver_updated != isinstance(self.detalle, DetalleConductorActualizado):
            raise ValueError("Invalid audit event")
        if password != isinstance(self.detalle, DetalleContrasena):
            raise ValueError("Invalid audit event")
        if incident != isinstance(self.detalle, DetalleIncidenciaRegistrada):
            raise ValueError("Invalid audit event")
        if isinstance(self.detalle, Detalle):
            permitido = self.evento is Evento.PERMITIDA
            if permitido != (self.detalle.motivo is Motivo.PERMITIDO):
                raise ValueError("Invalid audit decision")
            if permitido and (self.usuario_id is None or self.detalle.permiso is None):
                raise ValueError("Invalid audit decision")
        elif self.evento is Evento.LOGIN_FALLIDO and self.usuario_id is not None:
            raise ValueError("Failed login cannot have an authenticated actor")
        elif (parameter_update or deactivation) and (
            self.usuario_id is None or self.entidad_id is None
        ):
            raise ValueError("Invalid vehicle audit event")
        elif (driver_created or driver_updated) and (
            self.usuario_id is None or self.entidad_id is None
        ):
            raise ValueError("Invalid driver audit event")
        elif password and (self.usuario_id is None or self.entidad_id is None):
            raise ValueError("Invalid password audit event")
        elif (incident or resolution) and (
            self.usuario_id is None or self.entidad_id is None
        ):
            raise ValueError("Invalid incident audit event")
        return self


class AuditStorageError(RuntimeError):
    """Storage failed without exposing the driver error or parameters."""


class AuditoriaRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert(self, registro: Registro) -> None:
        registro = Registro.model_validate(registro)
        permiso = (
            registro.detalle.permiso if isinstance(registro.detalle, Detalle) else None
        )
        if permiso:
            entidad = permiso.value.split(".")[0]
        elif registro.evento in (
            Evento.LOGIN_EXITOSO,
            Evento.SESION_CERRADA,
            Evento.SESION_EXTENDIDA,
        ):
            entidad = "sesion"
        elif registro.evento in (
            Evento.LOGIN_FALLIDO,
            Evento.CUENTA_BLOQUEADA,
            Evento.CONTRASENA_RESTABLECIDA,
            Evento.CONTRASENA_CAMBIADA,
        ):
            entidad = "usuario"
        elif registro.evento in (
            Evento.VEHICULO_PARAMETROS_ACTUALIZADOS,
            Evento.VEHICULO_DESACTIVADO,
        ):
            entidad = "vehiculo"
        elif registro.evento in (
            Evento.CONDUCTOR_REGISTRADO,
            Evento.CONDUCTOR_ACTUALIZADO,
        ):
            entidad = "conductor"
        elif registro.evento in (
            Evento.INCIDENCIA_REGISTRADA,
            Evento.INCIDENCIA_RESUELTA,
        ):
            entidad = "incidencia"
        elif registro.evento is Evento.PARAMETROS_VERSIONADOS:
            entidad = "parametro"
        else:
            entidad = "autorizacion"
        row = Auditoria(
            usuario_id=registro.usuario_id,
            entidad=entidad,
            entidad_id=registro.entidad_id,
            accion=registro.evento.value,
            detalle=registro.detalle.model_dump(mode="json"),
        )
        try:
            self._session.add(row)
            self._session.flush()
        except SQLAlchemyError:
            raise AuditStorageError("Audit storage unavailable") from None
