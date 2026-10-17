"""Extraction pipeline: bytes in, cited fields out. Nothing is stored."""

from typing import List, Optional

from .documents import ParsedDocument, parse_document
from .fields import extract_fields, signals
from .models import Citation, DocumentInfo, ExtractedField, ExtractionResult, Page, Signal
from .segment import segment_document

RETENTION_NOTICE = (
    "Your file was processed in memory for this request only. PatientShield did not save it, log its contents, "
    "or send it to any other service. Closing or clearing this page removes it from your browser."
)


class CitationError(AssertionError):
    """Raised if a citation doesn't match the page text. This is a bug, never shown as a result."""


def _check(pages: List[str], citations: List[Citation]) -> None:
    for c in citations:
        if not (1 <= c.page <= len(pages)) or pages[c.page - 1][c.start : c.end] != c.quote:
            raise CitationError(f"citation does not match page {c.page} [{c.start}:{c.end}]")


def verify_citations(pages: List[str], fields: List[ExtractedField], sigs: List[Signal]) -> None:
    """Every quote must be the exact page text at its offsets: the core guarantee of the extractor."""
    for f in fields:
        _check(pages, f.citations)
    for s in sigs:
        _check(pages, s.citations)


def _warnings(doc: ParsedDocument, fields: List[ExtractedField], sigs: List[Signal]) -> List[str]:
    out: List[str] = []
    by_key = {f.key: f for f in fields}
    if any(s.kind == "suspicious" for s in sigs):
        out.append(
            "This document contains text addressed to software (for example, telling it to approve a claim). "
            "PatientShield ignores such text and only quotes it. Read the original letter carefully."
        )
    if (
        by_key["denial_reason"].status == "not_found"
        and not by_key["denial_reason"].citations
        and by_key["appeal_instructions"].status == "not_found"
    ):
        out.append("We couldn't find language that looks like a denial or appeal notice. Check that this is the right document.")
    if doc.truncated:
        out.append("This document was very long, so only the first part was read.")
    return out


def extract(name: str, data: bytes, synthetic: bool = False, sample_id: Optional[str] = None) -> ExtractionResult:
    doc = parse_document(name, data)
    passages = segment_document(doc.pages)
    fields = extract_fields(passages)
    sigs = signals(passages)
    verify_citations(doc.pages, fields, sigs)
    return ExtractionResult(
        document=DocumentInfo(
            name=doc.name,
            kind=doc.kind,  # type: ignore[arg-type]
            page_count=len(doc.pages),
            size_bytes=doc.size_bytes,
            synthetic=synthetic,
            sample_id=sample_id,
        ),
        pages=[Page(number=i, text=t) for i, t in enumerate(doc.pages, start=1)],
        fields=fields,
        signals=sigs,
        warnings=_warnings(doc, fields, sigs),
        retention=RETENTION_NOTICE,
    )
