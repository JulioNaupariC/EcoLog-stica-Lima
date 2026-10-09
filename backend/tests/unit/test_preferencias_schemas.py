import pytest
from pydantic import ValidationError

from app.schemas.preferencias import PreferenciasPatch

FIELDS = [("horario_preferido", 120), ("referencia", 255), ("restriccion_acceso", 255)]


@pytest.mark.parametrize("field,limit", FIELDS)
def test_limits_nullable_and_omitted(field, limit):
    assert PreferenciasPatch.model_validate({field: "ñ" * limit}).model_dump(
        exclude_unset=True
    ) == {field: "ñ" * limit}
    assert PreferenciasPatch.model_validate({field: None}).model_dump(
        exclude_unset=True
    ) == {field: None}
    with pytest.raises(ValidationError):
        PreferenciasPatch.model_validate({field: "x" * (limit + 1)})


@pytest.mark.parametrize("field,limit", FIELDS)
@pytest.mark.parametrize("value", ["", "  ", "\t\n", "a\x00b", 42, True, [], {}])
def test_bad_values_rejected(field, limit, value):
    with pytest.raises(ValidationError):
        PreferenciasPatch.model_validate({field: value})


def test_no_silent_normalization_or_schedule_conversion():
    data = PreferenciasPatch(horario_preferido="  Mañana (preferido)  ")
    assert data.horario_preferido == "  Mañana (preferido)  "


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"cliente_id": "other"},
        {"nombre": "name"},
        {"horario_preferido": None, "password": "secret"},
    ],
)
def test_empty_or_extra_fields_rejected(data):
    with pytest.raises(ValidationError):
        PreferenciasPatch.model_validate(data)
