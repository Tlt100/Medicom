"""Vercel entry point: exposes the FastAPI ASGI app as a Python serverless function."""

import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

try:
    from patientshield.app import app
except Exception:  # pragma: no cover - only reached when the deployment is misconfigured
    # Print the real cause to the function logs, and answer requests with a safe JSON error
    # instead of an opaque platform crash. No request data is involved at import time.
    traceback.print_exc(file=sys.stderr)
    _BODY = b'{"error":"server_error","message":"The PatientShield API failed to start."}'

    async def app(scope, receive, send):  # type: ignore[no-redef]
        if scope["type"] != "http":
            return
        await send(
            {
                "type": "http.response.start",
                "status": 503,
                "headers": [(b"content-type", b"application/json"), (b"cache-control", b"no-store")],
            }
        )
        await send({"type": "http.response.body", "body": _BODY})


__all__ = ["app"]
