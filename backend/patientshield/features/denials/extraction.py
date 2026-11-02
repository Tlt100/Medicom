"""Denial-letter extraction: the extractor the core document pipeline calls for doc_type "denial"."""

from typing import List, Optional

from patientshield.core.citations import check_document_citations
from patientshield.core.documents.models import DocumentInfo, Page
from patientshield.core.documents.parsing import ParsedDocument
from patientshield.core.documents.pipeline import RETENTION_NOTICE, process, register_extractor
from patientshield.core.documents.segment import segment_document
from patientshield.features.denials.fields import extract_fields, signals
from patientshield.features.denials.models import ExtractedField, ExtractionResult, Signal


def _warnings(doc: ParsedDocument, fields: List[ExtractedField], sigs: List[Signal]) -> List[str]:
    out: List[str] = []
    by_key = {f.key: f for f in fields}
    if any(s.kind == "suspicious" for s in sigs):
        out.append(
            "This document contains text addressed to software (for example, telling it to approve a claim). "
            "Medicom ignores such text and only quotes it. Read the original letter carefully."
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


def extract_denial(doc: ParsedDocument, info: DocumentInfo) -> ExtractionResult:
    passages = segment_document(doc.pages)
    fields = extract_fields(passages)
    sigs = signals(passages)
    # Every quote must be the exact page text at its offsets: the core guarantee of the extractor.
    for item in [*fields, *sigs]:
        check_document_citations(doc.pages, item.citations)
    return ExtractionResult(
        document=info,
        pages=[Page(number=i, text=t) for i, t in enumerate(doc.pages, start=1)],
        fields=fields,
        signals=sigs,
        warnings=_warnings(doc, fields, sigs),
        retention=RETENTION_NOTICE,
    )


register_extractor("denial", extract_denial)


def extract(name: str, data: bytes, synthetic: bool = False, sample_id: Optional[str] = None) -> ExtractionResult:
    """Convenience entry point: run the shared pipeline for a denial letter."""
    return process(name, data, "denial", synthetic=synthetic, sample_id=sample_id)  # type: ignore[return-value]
