"""ECL-84 / OWASP A02:2025: security headers on every API response.

Pure ASGI middleware, so it also covers errors, CORS preflights and /metrics.
The API only serves JSON, so its CSP forbids everything; the interactive docs
(/docs, /redoc) load Swagger/ReDoc assets and keep only ``frame-ancestors``.
HSTS is sent only with ``APP_ENV=production``, where the API is served over
HTTPS (enforced by ``Settings``); a development browser on plain HTTP must not
pin the local host.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CSP_API = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
CSP_DOCS = "frame-ancestors 'none'"
DOCS_PATHS = frozenset({"/docs", "/redoc", "/docs/oauth2-redirect"})
HSTS = "max-age=31536000; includeSubDomains"
COMMON = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-site",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, *, production: bool) -> None:
        self.app = app
        self.production = production

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        csp = CSP_DOCS if scope["path"] in DOCS_PATHS else CSP_API

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in COMMON.items():
                    headers.setdefault(name, value)
                headers.setdefault("Content-Security-Policy", csp)
                if self.production:
                    headers.setdefault("Strict-Transport-Security", HSTS)
            await send(message)

        await self.app(scope, receive, send_with_headers)
