"""Bill check API: compare an EOB with a bill, and synthetic sample pairs.

Uploads go through the shared POST /api/extract with X-Document-Type "eob" or "bill". The browser then sends the
extracted values (no page text, no names or account numbers) to POST /api/bill-check/compare.
"""

from typing import List, Literal

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import Response

from patientshield.core.documents.parsing import DocumentError
from patientshield.core.documents.pdfgen import render_pdf
from patientshield.core.documents.pipeline import process
from patientshield.core.routes.documents import document_error
from patientshield.features.bill_check.compare import compare
from patientshield.features.bill_check.extraction import to_input
from patientshield.features.bill_check.models import BillCheckSampleInfo, BillCheckSampleResult, CompareRequest, Comparison
from patientshield.features.bill_check.samples import SAMPLE_PAIRS, SAMPLE_PAIRS_BY_ID

router = APIRouter(prefix="/bill-check", tags=["bill-check"])

_SAMPLE_ID = Path(pattern=r"^[a-z0-9-]{1,60}$")


@router.post("/compare", response_model=Comparison)
def compare_documents(body: CompareRequest) -> Comparison:
    return compare(body.eob, body.bill)


@router.get("/samples", response_model=List[BillCheckSampleInfo])
def list_samples() -> List[BillCheckSampleInfo]:
    return [
        BillCheckSampleInfo(id=p.id, title=p.title, description=p.description, eob_filename=p.eob.filename, bill_filename=p.bill.filename)
        for p in SAMPLE_PAIRS
    ]


def _pair(sample_id: str):
    pair = SAMPLE_PAIRS_BY_ID.get(sample_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="Sample not found.")
    return pair


@router.post("/samples/{sample_id}", response_model=BillCheckSampleResult)
def run_sample(sample_id: str = _SAMPLE_ID):
    pair = _pair(sample_id)
    try:
        # The same PDF path as a real upload, on PDFs generated in memory.
        eob = process(pair.eob.filename, render_pdf(pair.eob), "eob", synthetic=True, sample_id=pair.id)
        bill = process(pair.bill.filename, render_pdf(pair.bill), "bill", synthetic=True, sample_id=pair.id)
    except DocumentError as exc:
        return document_error(exc)
    return BillCheckSampleResult(eob=eob, bill=bill, comparison=compare(to_input(eob), to_input(bill)))  # type: ignore[arg-type]


@router.get("/samples/{sample_id}/{doc}.pdf")
def download_sample(doc: Literal["eob", "bill"], sample_id: str = _SAMPLE_ID) -> Response:
    pair = _pair(sample_id)
    sample = pair.eob if doc == "eob" else pair.bill
    return Response(
        content=render_pdf(sample),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{sample.filename}"'},
    )
