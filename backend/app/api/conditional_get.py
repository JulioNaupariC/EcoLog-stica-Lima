"""ECL-110 / Green IT: ETag revalidation for cacheable JSON reads.

Pure ASGI middleware. For an eligible ``GET`` that answers ``200`` with JSON,
it adds a weak ``ETag`` computed from the uncompressed body and, if the
client already holds that version (``If-None-Match``), answers ``304 Not
Modified`` without a body. The browser cache sends ``If-None-Match`` by itself
when a ``fetch`` repeats the request, so the frontend needs no change.

Eligible responses, so personal data never ends up in a browser cache by
default:
- paths in ``ETAG_PATHS`` (catalogues without personal data, e.g. vehicles),
  which also get ``Cache-Control: private, no-cache`` when they had none;
- any response whose route already declared ``Cache-Control: private`` (for
  example the operational indicators).
Responses with ``no-store`` are never touched.

It must run inside ``GZipMiddleware``: the tag describes the JSON itself, not
its compressed form, and it is weak because the encoding may vary.
"""

from hashlib import sha256

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

ETAG_PATHS = ("/vehiculos",)
REVALIDATE = "private, no-cache"


def _eligible_path(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in ETAG_PATHS)


def _etag(body: bytes) -> str:
    return f'W/"{sha256(body).hexdigest()[:32]}"'


def _matches(if_none_match: str | None, etag: str) -> bool:
    """Weak comparison (RFC 9110 §13.1.2): the W/ prefix is ignored."""
    if not if_none_match:
        return False
    if if_none_match.strip() == "*":
        return True
    opaque = etag.removeprefix("W/")
    return any(
        candidate.strip().removeprefix("W/") == opaque
        for candidate in if_none_match.split(",")
    )


class ConditionalGetMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "GET":
            await self.app(scope, receive, send)
            return

        start: Message | None = None
        chunks: list[bytes] = []
        passthrough = False

        async def capture(message: Message) -> None:
            nonlocal start, passthrough
            if message["type"] == "http.response.start":
                start = message
                headers = Headers(raw=message["headers"])
                passthrough = not self._candidate(scope, headers)
                if passthrough:
                    await send(message)
                return
            if passthrough:
                await send(message)
                return
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                await self._finish(scope, start, b"".join(chunks), send)

        await self.app(scope, receive, capture)

    @staticmethod
    def _candidate(scope: Scope, headers: Headers) -> bool:
        cache_control = headers.get("cache-control", "").lower()
        if "no-store" in cache_control or "etag" in headers:
            return False
        if not headers.get("content-type", "").startswith("application/json"):
            return False
        return _eligible_path(scope["path"]) or "private" in cache_control

    @staticmethod
    async def _finish(
        scope: Scope, start: Message | None, body: bytes, send: Send
    ) -> None:
        assert start is not None
        if start["status"] != 200:
            await send(start)
            await send({"type": "http.response.body", "body": body})
            return
        headers = MutableHeaders(scope=start)
        etag = _etag(body)
        headers["ETag"] = etag
        if "cache-control" not in headers:
            headers["Cache-Control"] = REVALIDATE
        request_headers = Headers(scope=scope)
        if _matches(request_headers.get("if-none-match"), etag):
            start["status"] = 304
            for name in ("content-length", "content-type"):
                if name in headers:
                    del headers[name]
            await send(start)
            await send({"type": "http.response.body", "body": b""})
            return
        await send(start)
        await send({"type": "http.response.body", "body": body})
