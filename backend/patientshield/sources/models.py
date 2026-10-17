"""Typed models for the verified legal-source registry.

Kept compatible with Python 3.9 (local dev) and 3.12 (Vercel): use typing.Optional/List,
not the `X | None` syntax, because Pydantic evaluates annotations at runtime.
"""

import datetime as dt
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class SourceType(str, Enum):
    """How much legal weight a source carries. Always shown to the user."""

    statute = "statute"
    regulation = "regulation"
    agency_guidance = "agency-guidance"
    official_resource = "official-resource"
    educational = "educational"


BINDING_TYPES = {SourceType.statute, SourceType.regulation}


class Jurisdiction(str, Enum):
    federal = "US-Federal"
    nj = "NJ"


class Topic(str, Enum):
    internal_appeal = "internal-appeal"
    external_review = "external-review"
    plan_type = "plan-type"
    urgent = "urgent"
    medicaid = "medicaid"
    medicare = "medicare"
    denial_notice = "denial-notice"
    complaints = "complaints"


class Verification(str, Enum):
    verified = "verified"
    needs_review = "needs-review"


class Excerpt(BaseModel):
    model_config = ConfigDict(frozen=True)

    locator: str = Field(min_length=1, description='Where in the source, e.g. "§ 2560.503-1(h)(3)(i)"')
    text: str = Field(min_length=5, description="Verbatim text copied from the source on last_checked")


class Source(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=3)
    citation: Optional[str] = None
    authority: str
    url: HttpUrl
    jurisdiction: Jurisdiction
    source_type: SourceType
    topics: List[Topic] = Field(min_length=1)
    date: Optional[dt.date] = Field(None, description="Only set when the source itself showed it")
    date_label: Optional[str] = Field(None, description='What kind of date, e.g. "Content last reviewed"')
    last_checked: dt.date
    excerpts: List[Excerpt] = Field(default_factory=list)
    verification: Verification
    review_note: Optional[str] = None
    version: int = Field(ge=1)

    @field_validator("url")
    @classmethod
    def https_only(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme != "https":
            raise ValueError("source URLs must use https")
        return v

    @model_validator(mode="after")
    def consistency(self) -> "Source":
        if self.verification == Verification.verified and not self.excerpts:
            raise ValueError(f"{self.id}: verified sources need at least one verbatim excerpt")
        if self.verification == Verification.needs_review and not self.review_note:
            raise ValueError(f"{self.id}: needs-review sources must say what is unverified")
        if self.date is not None and not self.date_label:
            raise ValueError(f"{self.id}: a date needs a label saying what kind of date it is")
        return self

    @property
    def is_binding(self) -> bool:
        return self.source_type in BINDING_TYPES


class Coverage(BaseModel):
    total: int
    verified: int
    needs_review: int
    binding: int
    federal: int
    nj: int


class RegistryResponse(BaseModel):
    registry_version: int
    last_reviewed: dt.date
    coverage: Coverage
    sources: List[Source]
