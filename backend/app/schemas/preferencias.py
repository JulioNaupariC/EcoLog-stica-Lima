"""Client preferences; textual schedules are kept separate from order windows."""

from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    field_validator,
    model_validator,
)


class PreferenciasPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    horario_preferido: StrictStr | None = Field(default=None, max_length=120)
    referencia: StrictStr | None = Field(default=None, max_length=255)
    restriccion_acceso: StrictStr | None = Field(default=None, max_length=255)

    @field_validator("horario_preferido", "referencia", "restriccion_acceso")
    @classmethod
    def valid_text(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or "\x00" in value):
            raise ValueError("Use texto no vacío y sin caracteres nulos, o null")
        return value

    @model_validator(mode="after")
    def nonempty_patch(self) -> "PreferenciasPatch":
        if not self.model_fields_set:
            raise ValueError("Incluya al menos una preferencia")
        return self


class PreferenciasResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cliente_id: UUID
    horario_preferido: str | None
    referencia: str | None
    restriccion_acceso: str | None
