"""Minimal client projection for selectors; no preferences or contact data."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClienteListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cliente_id: UUID
    nombre: str


class ClientePage(BaseModel):
    items: list[ClienteListItem]
    page: int
    page_size: int
    total: int
