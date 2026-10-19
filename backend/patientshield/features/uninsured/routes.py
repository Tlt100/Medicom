"""GET /api/uninsured/rules: the versioned numbers and cited statements the browser needs to estimate eligibility.

There is deliberately no endpoint that accepts income: the estimate is computed in the browser.
"""

from typing import Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from patientshield.core.triage.models import ClaimOut
from patientshield.core.triage.service import claim_out
from patientshield.features.uninsured.rules import (
    CHARITY_CARE_BANDS,
    CHARITY_CARE_SOURCE,
    CLAIM_IDS,
    CURRENT_GUIDELINE_YEAR,
    DISCLAIMER,
    GUIDELINES,
    UNINSURED_CAP_BELOW_PERCENT,
    UNINSURED_CAP_MEDICARE_PERCENT,
    UNINSURED_CAP_SOURCE,
    CharityCareBand,
    PovertyGuideline,
)

router = APIRouter(prefix="/uninsured", tags=["uninsured"])


class UninsuredCap(BaseModel):
    below_percent: int
    medicare_percent: int
    source_id: str


class UninsuredRules(BaseModel):
    guideline: PovertyGuideline
    charity_care_bands: List[CharityCareBand]
    charity_care_source_id: str
    uninsured_cap: UninsuredCap
    claims: Dict[str, ClaimOut]
    disclaimer: str


@router.get("/rules", response_model=UninsuredRules)
def rules() -> UninsuredRules:
    return UninsuredRules(
        guideline=GUIDELINES[CURRENT_GUIDELINE_YEAR],
        charity_care_bands=CHARITY_CARE_BANDS,
        charity_care_source_id=CHARITY_CARE_SOURCE,
        uninsured_cap=UninsuredCap(
            below_percent=UNINSURED_CAP_BELOW_PERCENT, medicare_percent=UNINSURED_CAP_MEDICARE_PERCENT, source_id=UNINSURED_CAP_SOURCE
        ),
        claims={cid: claim_out(cid) for cid in CLAIM_IDS},
        disclaimer=DISCLAIMER,
    )
