"""Authenticated vehicle CRUD API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.dependencies import require_permission
from app.core.rbac import Identidad, Permiso
from app.schemas.vehiculo import VehicleCreate, VehicleResponse, VehicleUpdate
from app.services.vehiculos import (
    VehicleDuplicatePlate,
    VehicleInactive,
    VehicleNotFound,
    VehicleUnavailable,
    VehiculoService,
)

router = APIRouter(prefix="/vehiculos", tags=["vehiculos"])


def get_vehicle_service(request: Request) -> VehiculoService:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        )
    return VehiculoService(factory)


def _translate(operation):
    try:
        return operation()
    except VehicleNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Vehículo no encontrado"
        ) from None
    except (VehicleDuplicatePlate, VehicleInactive) as error:
        detail = (
            "La placa ya está registrada"
            if isinstance(error, VehicleDuplicatePlate)
            else "El vehículo no puede modificarse"
        )
        raise HTTPException(status.HTTP_409_CONFLICT, detail) from None
    except VehicleUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio no disponible"
        ) from None


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    payload: VehicleCreate,
    service: Annotated[VehiculoService, Depends(get_vehicle_service)],
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.VEHICULOS_CREAR))
    ],
) -> VehicleResponse:
    return VehicleResponse.model_validate(_translate(lambda: service.create(payload)))


@router.get("", response_model=list[VehicleResponse])
def list_vehicles(
    service: Annotated[VehiculoService, Depends(get_vehicle_service)],
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.VEHICULOS_CONSULTAR))
    ],
) -> list[VehicleResponse]:
    return [VehicleResponse.model_validate(row) for row in _translate(service.list_all)]


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(
    vehicle_id: UUID,
    service: Annotated[VehiculoService, Depends(get_vehicle_service)],
    _identity: Annotated[
        Identidad, Depends(require_permission(Permiso.VEHICULOS_CONSULTAR))
    ],
) -> VehicleResponse:
    return VehicleResponse.model_validate(_translate(lambda: service.get(vehicle_id)))


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(
    vehicle_id: UUID,
    payload: VehicleUpdate,
    service: Annotated[VehiculoService, Depends(get_vehicle_service)],
    identity: Annotated[
        Identidad, Depends(require_permission(Permiso.VEHICULOS_ACTUALIZAR))
    ],
) -> VehicleResponse:
    return VehicleResponse.model_validate(
        _translate(lambda: service.update(vehicle_id, payload, identity.usuario_id))
    )


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_vehicle(
    vehicle_id: UUID,
    service: Annotated[VehiculoService, Depends(get_vehicle_service)],
    identity: Annotated[
        Identidad, Depends(require_permission(Permiso.VEHICULOS_DESACTIVAR))
    ],
) -> Response:
    _translate(lambda: service.deactivate(vehicle_id, identity.usuario_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
