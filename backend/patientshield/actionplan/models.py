"""Request/response models for the action plan. Every client-sent value is bounded and typed."""

import datetime as dt
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..triage.models import ClaimOut, PlanType, SourceRef

_EARLIEST = dt.date(2000, 1, 1)


def _check_date(v: Optional[dt.date]) -> Optional[dt.date]:
    if v is None:
        return v
    if v < _EARLIEST or v > dt.date.today() + dt.timedelta(days=366):
        raise ValueError("date is outside the supported range")
    return v


class LetterQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    """A passage the client is quoting back from its own extraction result."""

    text: str = Field(min_length=1, max_length=600)
    page: int = Field(ge=1, le=30)


class StatedDeadline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=200)
    normalized: Optional[str] = Field(None, max_length=40)
    quote: LetterQuote


class LetterFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    letter_date: Optional[dt.date] = None
    denial_reason: Optional[LetterQuote] = None
    denial_statement: Optional[LetterQuote] = None
    appeal_instructions: List[LetterQuote] = Field(default_factory=list, max_length=6)
    appeal_deadline: Optional[StatedDeadline] = None
    other_time_limits: List[StatedDeadline] = Field(default_factory=list, max_length=6)
    external_review_deadline: Optional[StatedDeadline] = None
    urgent_mentioned: bool = False

    @field_validator("letter_date")
    @classmethod
    def _letter_date_range(cls, v: Optional[dt.date]) -> Optional[dt.date]:
        return _check_date(v)


class Situation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_received: Optional[dt.date] = None
    care_received: Literal["yes", "no", "unsure"] = "unsure"
    internal_appeal: Literal["not_yet", "waiting", "decided"] = "not_yet"
    final_decision_date: Optional[dt.date] = None
    urgent: Literal["yes", "no", "unsure"] = "unsure"

    @field_validator("date_received", "final_decision_date")
    @classmethod
    def _situation_date_range(cls, v: Optional[dt.date]) -> Optional[dt.date]:
        return _check_date(v)


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: Dict[str, str] = Field(max_length=10)
    letter: LetterFacts = Field(default_factory=LetterFacts)
    situation: Situation = Field(default_factory=Situation)


class Deadline(BaseModel):
    id: str
    label: str
    date: dt.date
    basis: str
    kind: Literal["letter", "rule"]
    claim: Optional[ClaimOut] = None
    quote: Optional[LetterQuote] = None
    days_left: int
    passed: bool
    note: Optional[str] = None


class Comparison(BaseModel):
    topic: str
    letter: Optional[LetterQuote]
    letter_status: Literal["found", "not_found"]
    letter_summary: str
    rules: List[ClaimOut]
    rules_summary: Optional[str] = None
    note: Optional[str] = None


class Step(BaseModel):
    id: str
    title: str
    detail: str
    kind: Literal["rule", "practical", "letter", "urgent"]
    due: Optional[dt.date] = None
    claims: List[ClaimOut] = Field(default_factory=list)
    quote: Optional[LetterQuote] = None


class Contact(BaseModel):
    name: str
    when: str
    phone: Optional[str] = None
    source: SourceRef
    claim: Optional[ClaimOut] = None


class ActionPlan(BaseModel):
    plan_type: PlanType
    label: str
    today: dt.date
    comparisons: List[Comparison]
    deadlines: List[Deadline]
    plan_around: Optional[str] = None
    steps: List[Step]
    documents: List[str]
    questions: List[str]
    contacts: List[Contact]
    uncertainties: List[str]
    disclaimer: str
