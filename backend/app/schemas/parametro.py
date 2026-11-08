"""EN-008 (ECL-26): API contract for versioned parameters."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.core.parametros import FUENTE_MAX, NOTA_MAX, REQUERIDOS, UNIDADES, VERSION_MAX

CodigoParametro = Literal[
    "PRECIO_COMBUSTIBLE_GALON",
    "LITROS_POR_GALON",
    "COSTO_MANTENIMIENTO_KM",
    "CAPTURA_CO2_ARBOL_ANIO",
]
Fuente = Annotated[str, Field(min_length=1, max_length=FUENTE_MAX, pattern=r"\S")]
CodigoVersion = Annotated[
    str, Field(min_length=1, max_length=VERSION_MAX, pattern=r"^[A-Z0-9][A-Z0-9._-]*$")
]


class ValorParametro(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    codigo: CodigoParametro
    valor: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=9)]
    unidad: str
    fuente: Fuente

    @model_validator(mode="after")
    def unidad_del_codigo(self) -> "ValorParametro":
        if self.unidad != UNIDADES[self.codigo]:
            raise ValueError(f"La unidad de {self.codigo} es {UNIDADES[self.codigo]}")
        return self


class VersionCreate(BaseModel):
    """A complete set: every required code once, each with its source."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    version: CodigoVersion
    vigente_desde: AwareDatetime
    nota: Annotated[str, Field(max_length=NOTA_MAX)] | None = None
    valores: list[ValorParametro] = Field(min_length=len(REQUERIDOS))

    @model_validator(mode="after")
    def conjunto_completo(self) -> "VersionCreate":
        codigos = [valor.codigo for valor in self.valores]
        if len(set(codigos)) != len(codigos):
            raise ValueError("Cada código aparece una sola vez")
        faltan = [codigo for codigo in REQUERIDOS if codigo not in codigos]
        if faltan:
            raise ValueError(f"Faltan parámetros requeridos: {', '.join(faltan)}")
        return self


class VersionResponse(BaseModel):
    version: str
    vigente_desde: AwareDatetime
    vigente_hasta: AwareDatetime | None
    nota: str | None
    valores: list[ValorParametro]
