"""Models for comparing a provider's bill with the insurer's Explanation of Benefits (EOB).

Money is always whole cents (int) so totals add up exactly.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from patientshield.core.citations import DocumentCitation
from patientshield.core.documents.models import DocumentInfo, Page
from patientshield.core.triage.models import ClaimOut

# Columns PatientShield recognizes on an EOB or a bill. Anything else on the row is ignored, never guessed.
ColumnKey = Literal[
    "billed",  # the provider's charge
    "allowed",  # the plan's allowed amount
    "plan_paid",  # what the plan paid
    "deductible",
    "copay",
    "coinsurance",
    "not_covered",
    "patient_owes",  # what the EOB says you owe for the line
    "adjustment",
    "patient_paid",
    "balance",
]

TotalKey = Literal["patient_owes", "amount_due", "total_charges", "insurance_paid", "adjustments", "patient_paid"]

MAX_CENTS = 100_000_000_00  # $100 million: far above any real bill, rejects absurd input


class LineItem(BaseModel):
    """One service row from an EOB or a bill, quoted exactly from the page."""

    id: str
    service_date: Optional[str] = Field(None, description="ISO date, if the row shows one")
    code: Optional[str] = Field(None, description="CPT or HCPCS code, if the row shows one")
    description: str
    amounts: Dict[ColumnKey, int] = Field(default_factory=dict, description="Cents, by column")
    status: Literal["listed", "denied"] = "listed"
    citation: DocumentCitation


class Total(BaseModel):
    key: TotalKey
    label: str
    amount_cents: int
    citation: DocumentCitation


class LineItemExtraction(BaseModel):
    """What was read from one EOB or bill. Returned by POST /api/extract for doc types "eob" and "bill"."""

    document: DocumentInfo
    pages: List[Page]
    columns: List[ColumnKey]
    line_items: List[LineItem]
    totals: List[Total]
    warnings: List[str]
    retention: str


# ------------------------------------------------------------------ comparison input (from the browser)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LineItemIn(_Strict):
    id: str = Field(pattern=r"^(eob|bill)-[0-9]{1,4}$")
    service_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    code: Optional[str] = Field(None, pattern=r"^[A-Z0-9]{5}$")
    description: str = Field(max_length=200)
    amounts: Dict[ColumnKey, int] = Field(default_factory=dict)
    status: Literal["listed", "denied"] = "listed"

    @field_validator("amounts")
    @classmethod
    def bounded(cls, v: Dict[str, int]) -> Dict[str, int]:
        if any(abs(c) > MAX_CENTS for c in v.values()):
            raise ValueError("amount out of range")
        return v


class TotalIn(_Strict):
    key: TotalKey
    amount_cents: int = Field(ge=-MAX_CENTS, le=MAX_CENTS)


class DocumentIn(_Strict):
    line_items: List[LineItemIn] = Field(max_length=200)
    totals: List[TotalIn] = Field(default_factory=list, max_length=20)


class CompareRequest(_Strict):
    eob: DocumentIn
    bill: DocumentIn


# ------------------------------------------------------------------ comparison output

FlagKind = Literal[
    "amount_due_exceeds_eob",
    "possible_duplicate",
    "not_on_eob",
    "charge_differs",
    "denied_on_eob",
    "on_eob_not_on_bill",
    "amount_due_below_eob",
    "no_line_items",
    "surprise_bill_context",
]


class Flag(BaseModel):
    id: str
    kind: FlagKind
    level: Literal["ask", "info"] = Field(description='"ask": worth asking about. "info": good to know.')
    title: str
    detail: str
    bill_item_ids: List[str] = Field(default_factory=list)
    eob_item_ids: List[str] = Field(default_factory=list)
    claims: List[ClaimOut] = Field(default_factory=list)
    practical: bool = Field(False, description="A practical suggestion, not a rule from a source")


class Match(BaseModel):
    bill_item_id: str
    eob_item_id: str
    matched_on: List[Literal["date", "code", "charge", "description"]]


class Comparison(BaseModel):
    matches: List[Match]
    flags: List[Flag]
    eob_patient_owes_cents: Optional[int]
    bill_amount_due_cents: Optional[int]
    next_steps: List[ClaimOut]
    disclaimer: str


class BillCheckSampleInfo(BaseModel):
    id: str
    title: str
    description: str
    eob_filename: str
    bill_filename: str


class BillCheckSampleResult(BaseModel):
    eob: LineItemExtraction
    bill: LineItemExtraction
    comparison: Comparison
