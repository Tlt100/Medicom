"""GET /api/benchmarks: Medicare reference amounts for common services, with how they were made and their sources."""

from typing import Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from patientshield.core.benchmarks import data
from patientshield.core.triage.models import ClaimOut
from patientshield.core.triage.service import claim_out

router = APIRouter(tags=["benchmarks"])

CLAIM_IDS = [
    "medicare_estimate_how",
    "medicare_facility_rate",
    "price_transparency_list",
    "price_transparency_shoppable",
    "price_terms",
    "nj_uninsured_cap",
]

DISCLAIMER = (
    "Medicare amounts are a reference point, not what you owe. Your coverage, the hospital’s contracts and its financial "
    "assistance rules decide what you pay. A difference from the Medicare amount is context for a question, not evidence "
    "that a charge is wrong."
)


class Locality(BaseModel):
    id: str
    name: str


class BenchmarkRate(BaseModel):
    code: str
    label: str
    category: str
    setting: str
    covers: str
    # False when a bill's charge for this code usually covers more than this amount (emergency visits: the
    # hospital's own charges), so a ratio would mislead.
    comparable: bool
    amounts_cents: Dict[str, int]  # by locality id


class BenchmarksResponse(BaseModel):
    year: int
    version: str
    file_updated: str
    retrieved: str
    conversion_factor: str
    localities: List[Locality]
    northern_nj_counties: List[str]
    nj_counties: List[str]
    rates: List[BenchmarkRate]
    source_ids: List[str]
    claims: Dict[str, ClaimOut]
    disclaimer: str


def benchmarks() -> BenchmarksResponse:
    return BenchmarksResponse(
        year=data.YEAR,
        version=data.VERSION,
        file_updated=data.FILE_UPDATED,
        retrieved=data.RETRIEVED,
        conversion_factor=str(data.CONVERSION_FACTOR),
        localities=[Locality(id=k, name=v) for k, v in data.LOCALITY_NAMES.items()],
        northern_nj_counties=data.NORTHERN_NJ_COUNTIES,
        nj_counties=data.NJ_COUNTIES,
        rates=[
            BenchmarkRate(
                code=s.code,
                label=s.label,
                category=s.category,
                setting=s.setting,
                covers=data.COVERS[s.category],
                comparable=s.category != "emergency",
                amounts_cents={loc: data.amount_cents(s, loc) for loc in data.GPCI},
            )
            for s in data.SERVICES
        ],
        source_ids=data.SOURCE_IDS,
        claims={cid: claim_out(cid) for cid in CLAIM_IDS},
        disclaimer=DISCLAIMER,
    )


@router.get("/benchmarks", response_model=BenchmarksResponse)
def get_benchmarks() -> BenchmarksResponse:
    return benchmarks()
