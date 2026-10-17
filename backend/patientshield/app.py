"""FastAPI application factory. All routes live under /api so Vercel can route them to one function."""

import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from .config import Settings, get_settings
from .routers import documents, health, sources
from .security import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from .sources.service import load_sources

logger = logging.getLogger("patientshield")


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or get_settings()
    load_sources()  # fail fast on a malformed registry

    app = FastAPI(
        title="PatientShield API",
        version=__version__,
        docs_url="/api/docs" if settings.enable_docs else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.enable_docs else None,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse({"error": "http_error", "message": detail}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Report which fields failed without echoing user-supplied values back.
        fields = [".".join(str(p) for p in err.get("loc", ())) for err in exc.errors()]
        return JSONResponse({"error": "invalid_request", "message": "Some inputs were invalid.", "fields": fields}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        # Log the type only. Never log request bodies or document text.
        logger.error("unhandled error: %s", type(exc).__name__)
        return JSONResponse({"error": "server_error", "message": "Something went wrong on our side."}, status_code=500)

    app.include_router(health.router, prefix="/api")
    app.include_router(sources.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    return app


app = create_app()
