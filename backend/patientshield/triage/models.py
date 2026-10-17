from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

PlanType = Literal[
    "nj-regulated",
    "marketplace",
    "self-funded",
    "medicaid",
    "medicare",
    "other-state",
    "government-or-religious",
    "unknown",
]


class OptionOut(BaseModel):
    value: str
    label: str
    hint: Optional[str] = None
    next: Optional[str] = None


class QuestionOut(BaseModel):
    id: str
    prompt: str
    help: str
    options: List[OptionOut]


class FlowOut(BaseModel):
    start: str
    questions: Dict[str, QuestionOut]


class SuggestRequest(BaseModel):
    signals: List[str] = Field(default_factory=list, max_length=20)


class Suggestion(BaseModel):
    answers: Dict[str, str]
    reasons: List[str]


class TriageRequest(BaseModel):
    answers: Dict[str, str] = Field(max_length=10)


class SourceRef(BaseModel):
    id: str
    title: str
    citation: Optional[str]
    authority: str
    url: str
    source_type: str
    verification: Literal["verified", "needs-review"]


class ClaimOut(BaseModel):
    id: str
    text: str
    sources: List[SourceRef]
    needs_review: bool


class AnswerOut(BaseModel):
    question: str
    answer: str


class Regulator(BaseModel):
    name: str
    source: Optional[SourceRef] = None


class TriageResult(BaseModel):
    plan_type: PlanType
    label: str
    confidence: Literal["confirmed", "needs-confirmation"]
    summary: str
    regulator: Optional[Regulator]
    claims: List[ClaimOut]
    uncertainties: List[str]
    how_to_confirm: List[str]
    answers: List[AnswerOut]
