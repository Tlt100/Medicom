"""HTTP hardening shared by every API response. Plain ASGI middleware (no BaseHTTPMiddleware)."""

import json
import re
from typing import Iterable, List, Union

from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

API_SECURITY_HEADERS = {
    # The API only ever returns JSON; nothing it serves should be rendered or framed.
    "content-security-policy": "default-src 'none'; frame-ancestors 'none'",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "x-frame-options": "DENY",
    "cross-origin-resource-policy": "same-origin",
    # Responses may describe a user's document; never let browsers or proxies cache them.
    "cache-control": "no-store",
}


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {k.decode("latin-1").lower() for k, _ in headers}
                for key, value in API_SECURITY_HEADERS.items():
                    if key not in present:
                        headers.append((key.encode("latin-1"), value.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


class BodyTooLarge(HTTPException):
    """Raised while reading a request body that exceeds the limit. It's an HTTPException so FastAPI's body
    parser re-raises it instead of converting it into a generic 400; the app maps it to a 413 response."""

    def __init__(self) -> None:
        super().__init__(status_code=413, detail="Request is too large.")


async def _send_json(send: Send, status: int, body: dict) -> None:
    payload = json.dumps(body).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(payload)).encode())]
            + [(k.encode(), v.encode()) for k, v in API_SECURITY_HEADERS.items()],
        }
    )
    await send({"type": "http.response.body", "body": payload})


def too_large_body(max_bytes: int) -> dict:
    return {"error": "too_large", "message": f"Request is too large. The limit is {max_bytes / 1024 / 1024:.0f} MB."}


class BodySizeLimitMiddleware:
    """Caps request bodies two ways: by Content-Length up front, and by counting bytes as they stream in
    (so chunked requests without a Content-Length can't exhaust memory)."""

    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        for key, value in scope.get("headers", []):
            if key == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    return await _send_json(send, 400, {"error": "invalid_request", "message": "Invalid Content-Length header."})
                if declared > self.max_bytes:
                    return await _send_json(send, 413, too_large_body(self.max_bytes))

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise BodyTooLarge()
            return message

        await self.app(scope, limited_receive, send)


_SAFE_LOC = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,39}$")


def safe_error_fields(errors: Iterable[dict]) -> List[str]:
    """Field paths for validation errors, with any part that isn't a plain identifier or index masked.
    Dict keys in a request body are user input, so they are never echoed back."""
    out: List[str] = []
    for err in errors:
        parts: List[Union[str, int]] = []
        for part in err.get("loc", ()):
            if isinstance(part, int) or (isinstance(part, str) and _SAFE_LOC.match(part)):
                parts.append(part)
            else:
                parts.append("*")
        out.append(".".join(str(p) for p in parts))
    return out
