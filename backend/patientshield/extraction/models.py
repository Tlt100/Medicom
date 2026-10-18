"""Response models for document extraction."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

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


class Citation(BaseModel):
    """An exact span of a page's text. Invariant: pages[page-1].text[start:end] == quote."""

    page: int = Field(ge=1)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    quote: str


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


class Page(BaseModel):
    number: int
    text: str


class DocumentInfo(BaseModel):
    name: str
    kind: Literal["pdf", "text"]
    page_count: int
    size_bytes: int
    synthetic: bool
    sample_id: Optional[str] = None


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
