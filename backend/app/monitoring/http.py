"""Pure ASGI instrumentation, including unhandled errors and active requests."""

from time import perf_counter

from starlette.routing import compile_path
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.monitoring.metrics import Metrics


class MetricsMiddleware:
    def __init__(self, app: ASGIApp, metrics: Metrics) -> None:
        self.app = app
        self.metrics = metrics

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] == "/metrics":
            await self.app(scope, receive, send)
            return
        started = perf_counter()
        method = scope["method"]
        if method not in {"GET", "POST", "PATCH", "PUT", "DELETE", "HEAD", "OPTIONS"}:
            method = "OTHER"
        route = "unmatched"
        # OpenAPI provides public route templates across FastAPI router versions.
        for path, operations in scope["app"].openapi()["paths"].items():
            if compile_path(path)[0].match(scope["path"]):
                route = path
                if scope["method"].lower() in operations:
                    break
        if scope["path"] in {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/docs/oauth2-redirect",
        }:
            route = scope["path"]
        key = (method, route)
        status = 500
        self.metrics.inflight(key, 1)

        async def measured_send(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, measured_send)
        except BaseException as error:
            if not isinstance(error, Exception):
                status = 0
            self.metrics.increment("ecolog_http_exceptions_total", key)
            raise
        finally:
            self.metrics.inflight(key, -1)
            self.metrics.increment(
                "ecolog_http_requests_total",
                key + (str(status) if status else "no_response",),
            )
            if 500 <= status <= 599:
                self.metrics.increment("ecolog_http_5xx_total", key)
            self.metrics.observe(
                "ecolog_http_request_duration_seconds",
                key + (str(status) if status else "no_response",),
                perf_counter() - started,
            )
