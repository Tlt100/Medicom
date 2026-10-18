"""Response models for denial-letter extraction. Citations, pages and document info come from core."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from patientshield.core.citations import Citation
from patientshield.core.documents.models import DocumentInfo, Page

__all__ = ["Citation", "DocumentInfo", "Page", "FieldKey", "ExtractedField", "Signal", "ExtractionResult", "SampleInfo"]

FieldKey = Literal[
    "denial_reason",
    "appeal_instructions",
    "appeal_deadline",
    "external_review_deadline",
    "letter_date",
    "insurer_name",
    "plan_name",
    "reference_numbers",
]


class ExtractedField(BaseModel):
    key: FieldKey
    label: str
    status: Literal["found", "not_found"]
    value: Optional[str] = None
    values: List[str] = Field(default_factory=list)
    normalized: Optional[str] = Field(None, description="Machine-readable form, e.g. ISO date or day count")
    citations: List[Citation] = Field(default_factory=list)
    confidence: Optional[Literal["high", "medium"]] = None
    note: Optional[str] = None


class Signal(BaseModel):
    kind: Literal["plan-type", "urgent", "suspicious"]
    code: str
    label: str
    citations: List[Citation]


class ExtractionResult(BaseModel):
    document: DocumentInfo
    pages: List[Page]
    fields: List[ExtractedField]
    signals: List[Signal]
    warnings: List[str]
    retention: str


class SampleInfo(BaseModel):
    id: str
    title: str
    description: str
    scenario: str
    filename: str
    page_count: int
