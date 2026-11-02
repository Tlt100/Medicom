"""FastAPI application factory. All routes live under /api so Vercel can route them to one function."""

import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from patientshield import __version__
from patientshield.core.benchmarks import routes as benchmarks
from patientshield.core.config import Settings, get_settings
from patientshield.core.routes import claims, documents, health, sources, triage
from patientshield.core.security import BodySizeLimitMiddleware, BodyTooLarge, SecurityHeadersMiddleware, safe_error_fields, too_large_body
from patientshield.core.sources.service import load_sources
from patientshield.features import bill_check, denials, uninsured

logger = logging.getLogger("patientshield")


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or get_settings()
    load_sources()  # fail fast on a malformed registry

    app = FastAPI(
        title="Medicom API",
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
        # Report which fields failed without echoing user-supplied values (or user-chosen keys) back.
        fields = safe_error_fields(exc.errors())
        return JSONResponse({"error": "invalid_request", "message": "Some inputs were invalid.", "fields": fields}, status_code=422)

    @app.exception_handler(BodyTooLarge)
    async def body_too_large(_: Request, __: BodyTooLarge) -> JSONResponse:
        return JSONResponse(too_large_body(settings.max_request_bytes), status_code=413)

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        # Log the type only. Never log request bodies or document text.
        logger.error("unhandled error: %s", type(exc).__name__)
        return JSONResponse({"error": "server_error", "message": "Something went wrong on our side."}, status_code=500)

    # Core routes shared by every feature.
    for module in (health, sources, claims, triage, documents, benchmarks):
        app.include_router(module.router, prefix="/api")
    # Feature routes.
    for router in [*denials.ROUTERS, *bill_check.ROUTERS, *uninsured.ROUTERS]:
        app.include_router(router, prefix="/api")
    return app


app = create_app()
