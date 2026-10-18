"""The citation system shared by every feature.

A statement in PatientShield is backed by one of two kinds of citation:
- a DocumentCitation: an exact span of the user's own document (page + offsets + the quoted text), or
- a SourceCitation: an entry in the verified source library (see core.sources), optionally a specific excerpt.

Document citations are verified against the page text before anything is returned, and re-verified by the
browser; a quote that doesn't match is a bug and is never shown.
"""

from typing import Iterable, List, Optional

from pydantic import BaseModel, Field


class DocumentCitation(BaseModel):
    """An exact span of a page's text. Invariant: pages[page-1].text[start:end] == quote."""

    page: int = Field(ge=1)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    quote: str


# The name used throughout the denial feature and its API schema.
Citation = DocumentCitation


class SourceCitation(BaseModel):
    """A pointer into the verified source library."""

    source_id: str = Field(pattern=r"^[a-z0-9-]{1,80}$")
    locator: Optional[str] = Field(None, description='A specific excerpt, e.g. "§ 2560.503-1(h)(3)(i)"')


class CitationError(AssertionError):
    """Raised if a document citation doesn't match the page text. This is a bug, never shown as a result."""


def check_document_citations(pages: List[str], citations: Iterable[DocumentCitation]) -> None:
    for c in citations:
        if not (1 <= c.page <= len(pages)) or pages[c.page - 1][c.start : c.end] != c.quote:
            raise CitationError(f"citation does not match page {c.page} [{c.start}:{c.end}]")


def check_source_citations(citations: Iterable[SourceCitation]) -> None:
    from patientshield.core.sources.service import get_source  # local import: sources load the registry

    for c in citations:
        source = get_source(c.source_id)
        if source is None:
            raise CitationError(f"unknown source {c.source_id}")
        if c.locator is not None and c.locator not in {e.locator for e in source.excerpts}:
            raise CitationError(f"source {c.source_id} has no excerpt at {c.locator}")
