"""HTTP hardening shared by every API response."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

API_SECURITY_HEADERS = {
    # The API only ever returns JSON; nothing it serves should be rendered or framed.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Resource-Policy": "same-origin",
    # Responses may describe a user's document; never let browsers or proxies cache them.
    "Cache-Control": "no-store",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for key, value in API_SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects oversized requests before the body is read, based on Content-Length."""

    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        length = request.headers.get("content-length")
        if length is not None:
            try:
                too_big = int(length) > self.max_bytes
            except ValueError:
                return JSONResponse({"error": "invalid_request", "message": "Invalid Content-Length header."}, status_code=400)
            if too_big:
                mb = self.max_bytes / 1024 / 1024
                return JSONResponse(
                    {"error": "too_large", "message": f"Request is too large. The limit is {mb:.0f} MB."},
                    status_code=413,
                )
        return await call_next(request)
