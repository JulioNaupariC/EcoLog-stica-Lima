"""Route class whose 422 responses never echo the submitted input."""

from collections.abc import Callable

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute


class SanitizedRoute(APIRoute):
    """FastAPI includes `input` in validation errors; passwords and personal data
    (DNI, phone) must not appear. Shared by drivers, users and password change."""

    def get_route_handler(self) -> Callable:
        handler = super().get_route_handler()

        async def sanitized(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError as error:
                details = [
                    {
                        "loc": item["loc"],
                        "type": item["type"],
                        "msg": "Entrada inválida",
                    }
                    for item in error.errors()
                ]
                return JSONResponse(status_code=422, content={"detail": details})

        return sanitized
