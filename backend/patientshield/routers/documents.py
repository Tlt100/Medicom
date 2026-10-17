"""Upload and sample-letter endpoints.

Uploads are sent as the raw request body (not multipart) with the file name in an X-File-Name header.
That avoids a multipart parser on the attack surface and lets the server stop reading at the size limit.
"""

from typing import List
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Path, Request
from fastapi.responses import JSONResponse, Response

from ..extraction.documents import MAX_BYTES, DocumentError
from ..extraction.models import ExtractionResult, SampleInfo
from ..extraction.service import extract
from ..samples.letters import SAMPLES, SAMPLES_BY_ID
from ..samples.pdfgen import render_pdf

router = APIRouter(tags=["documents"])

_SAMPLE_ID = Path(pattern=r"^[a-z0-9-]{1,60}$")


def _error(exc: DocumentError) -> JSONResponse:
    return JSONResponse({"error": exc.code, "message": exc.message}, status_code=exc.status)


async def _read_limited(request: Request, limit: int) -> bytes:
    """Reads the body but stops as soon as it exceeds the limit, even without a Content-Length header."""
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise DocumentError("too_large", f"This file is larger than the {limit // (1024 * 1024)} MB limit.", status=413)
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/extract", response_model=ExtractionResult)
async def extract_upload(request: Request):
    raw_name = request.headers.get("x-file-name", "document")
    name = unquote(raw_name)[:200]
    try:
        data = await _read_limited(request, MAX_BYTES)
        return extract(name, data)
    except DocumentError as exc:
        return _error(exc)


@router.get("/samples", response_model=List[SampleInfo])
def list_samples() -> List[SampleInfo]:
    return [
        SampleInfo(
            id=s.id,
            title=s.title,
            description=s.description,
            scenario=s.scenario,
            filename=s.filename,
            page_count=len(s.pages),
        )
        for s in SAMPLES
    ]


def _sample(sample_id: str):
    sample = SAMPLES_BY_ID.get(sample_id)
    if sample is None:
        raise HTTPException(status_code=404, detail="Sample letter not found.")
    return sample


@router.post("/samples/{sample_id}/extract", response_model=ExtractionResult)
def extract_sample(sample_id: str = _SAMPLE_ID):
    sample = _sample(sample_id)
    try:
        # Runs the same PDF path as a real upload, on a PDF generated in memory.
        return extract(sample.filename, render_pdf(sample), synthetic=True, sample_id=sample.id)
    except DocumentError as exc:
        return _error(exc)


@router.get("/samples/{sample_id}/pdf")
def download_sample(sample_id: str = _SAMPLE_ID) -> Response:
    sample = _sample(sample_id)
    return Response(
        content=render_pdf(sample),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{sample.filename}"'},
    )
