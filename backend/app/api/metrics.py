"""Protected metrics and a readiness probe without private internals."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from app.api.dependencies import require_permission
from app.core.rbac import Identidad, Permiso
from app.monitoring.probe import probe_database

router = APIRouter()


class ReadinessResponse(BaseModel):
    status: str
    database: str
    database_latency_seconds: float


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    tags=["health"],
    responses={
        503: {"model": ReadinessResponse, "description": "Database unavailable"}
    },
)
def readiness(request: Request, response: Response) -> ReadinessResponse:
    available, elapsed = probe_database(
        request.app.state.probe_engine, request.app.state.metrics
    )
    response.status_code = 200 if available else 503
    response.headers["Cache-Control"] = "no-store"
    return ReadinessResponse(
        status="ok" if available else "unavailable",
        database="up" if available else "down",
        database_latency_seconds=elapsed,
    )


@router.get(
    "/metrics",
    tags=["monitoring"],
    response_class=Response,
    responses={
        200: {"content": {"text/plain": {"schema": {"type": "string"}}}},
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied"},
        503: {"description": "Authentication or audit unavailable"},
    },
)
def metrics(
    request: Request,
    identity: Annotated[
        Identidad, Depends(require_permission(Permiso.INDICADORES_CONSULTAR))
    ],
) -> Response:
    return Response(
        request.app.state.metrics.render(),
        headers={"Cache-Control": "no-store"},
        media_type="text/plain; version=0.0.4",
    )
