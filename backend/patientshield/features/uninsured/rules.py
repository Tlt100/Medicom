"""Versioned rules for uninsured New Jersey hospital patients.

Every number here is copied from a verified source in the registry, and tests check that it still appears there:
- HHS poverty guidelines (hhs-poverty-guidelines-2026, fr-2026-00755)
- NJ Charity Care income bands (nj-doh-charity-care)
- the 500% / 115% limit in P.L.2008, c.60 (nj-pl-2008-c60), flagged for review: the Department of Health's sliding
  scale under that law has not been confirmed.
Money is whole cents. Percentages are whole numbers of percent.
"""

from typing import Dict, List

from pydantic import BaseModel


class PovertyGuideline(BaseModel):
    year: int
    region: str
    effective: str
    first_person_cents: int
    additional_person_cents: int
    by_household_size: List[int]  # sizes 1..8; larger households add additional_person_cents each
    source_ids: List[str]


class CharityCareBand(BaseModel):
    """Income above the previous band's limit and at or below `max_percent` pays `patient_share_percent` of the charge."""

    max_percent: int
    patient_share_percent: int


GUIDELINES: Dict[int, PovertyGuideline] = {
    2026: PovertyGuideline(
        year=2026,
        region="48 contiguous states and DC",
        effective="2026-01-13",
        first_person_cents=1_596_000,
        additional_person_cents=568_000,
        by_household_size=[1_596_000, 2_164_000, 2_732_000, 3_300_000, 3_868_000, 4_436_000, 5_004_000, 5_572_000],
        source_ids=["hhs-poverty-guidelines-2026", "fr-2026-00755"],
    ),
}
CURRENT_GUIDELINE_YEAR = 2026

CHARITY_CARE_BANDS: List[CharityCareBand] = [
    CharityCareBand(max_percent=200, patient_share_percent=0),
    CharityCareBand(max_percent=225, patient_share_percent=20),
    CharityCareBand(max_percent=250, patient_share_percent=40),
    CharityCareBand(max_percent=275, patient_share_percent=60),
    CharityCareBand(max_percent=300, patient_share_percent=80),
]
CHARITY_CARE_SOURCE = "nj-doh-charity-care"

# P.L.2008, c.60: family gross income *less than* 500% of the federal poverty level; no more than 115% of the Medicare rate.
UNINSURED_CAP_BELOW_PERCENT = 500
UNINSURED_CAP_MEDICARE_PERCENT = 115
UNINSURED_CAP_SOURCE = "nj-pl-2008-c60"

CLAIM_IDS = [
    "nj_uninsured_cap",
    "nj_uninsured_sliding_scale",
    "charity_care_what",
    "charity_care_who",
    "charity_care_income",
    "charity_care_assets",
    "charity_care_apply",
    "charity_care_medicaid_first",
    "charity_care_not_everything",
    "charity_care_hotline",
    "poverty_guidelines_2026",
    "good_faith_estimate",
]

DISCLAIMER = (
    "This is an estimate of what you may be eligible for, not a decision. The hospital decides Charity Care and how it "
    "applies New Jersey’s limit on charges, using its own application and documents. Medicom doesn’t decide "
    "whether a bill is correct."
)
