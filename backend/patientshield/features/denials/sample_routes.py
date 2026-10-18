"""Synthetic sample letters for demo mode. They run through the same pipeline as a real upload."""

from typing import List

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import Response

from patientshield.core.documents.parsing import DocumentError
from patientshield.core.documents.pdfgen import render_pdf
from patientshield.core.routes.documents import document_error
from patientshield.features.denials.extraction import extract
from patientshield.features.denials.models import ExtractionResult, SampleInfo
from patientshield.features.denials.samples import SAMPLES, SAMPLES_BY_ID

router = APIRouter(tags=["denials"])

_SAMPLE_ID = Path(pattern=r"^[a-z0-9-]{1,60}$")


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
        return document_error(exc)


@router.get("/samples/{sample_id}/pdf")
def download_sample(sample_id: str = _SAMPLE_ID) -> Response:
    sample = _sample(sample_id)
    return Response(
        content=render_pdf(sample),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{sample.filename}"'},
    )
