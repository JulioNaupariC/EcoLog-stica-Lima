
"""Import models to register their Alembic metadata."""

from app.models.auditoria import Auditoria
from app.models.cliente import Cliente
from app.models.conductor import Conductor
from app.models.pedido import Pedido
from app.models.sesion import Sesion
from app.models.usuario import Usuario
from app.models.vehiculo import Vehiculo

__all__ = [
    "Auditoria",
    "Cliente",
    "Conductor",
    "Pedido",
    "Sesion",
    "Usuario",
    "Vehiculo",
]
