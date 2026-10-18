"""The single upload endpoint for every document type.

Uploads are sent as the raw request body (not multipart) with the file name in an X-File-Name header and the
document type in X-Document-Type (default "denial"). That avoids a multipart parser on the attack surface and
lets the server stop reading at the size limit.
"""

from typing import get_args
from urllib.parse import unquote

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from patientshield.core.documents.models import DocumentType
from patientshield.core.documents.parsing import MAX_BYTES, DocumentError
from patientshield.core.documents.pipeline import process

router = APIRouter(tags=["documents"])

_DOCUMENT_TYPES = set(get_args(DocumentType))


def document_error(exc: DocumentError) -> JSONResponse:
    return JSONResponse({"error": exc.code, "message": exc.message}, status_code=exc.status)


async def read_limited(request: Request, limit: int) -> bytes:
    """Reads the body but stops as soon as it exceeds the limit, even without a Content-Length header."""
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise DocumentError("too_large", f"This file is larger than the {limit // (1024 * 1024)} MB limit.", status=413)
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/extract")
async def extract_upload(request: Request):
    name = unquote(request.headers.get("x-file-name", "document"))[:200]
    doc_type = request.headers.get("x-document-type", "denial").strip().lower()
    if doc_type not in _DOCUMENT_TYPES:
        return JSONResponse(
            {"error": "invalid_document_type", "message": "Unknown document type. Use denial, eob or bill."}, status_code=422
        )
    try:
        data = await read_limited(request, MAX_BYTES)
        # Parsing is CPU-bound; run it in a worker thread so it never blocks the event loop.
        return await run_in_threadpool(process, name, data, doc_type)
    except DocumentError as exc:
        return document_error(exc)
