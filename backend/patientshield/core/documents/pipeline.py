"""The document pipeline shared by every feature: validate → parse → hand off to the feature's extractor.

Features register an extractor for the document type they understand (denial letters today; EOBs and bills
when those modules are built). A document type with no extractor is refused with an honest message instead
of a guess. Nothing is stored: bytes live only for the duration of one call, and the caller (the browser)
deletes its copy explicitly.
"""

from typing import Callable, Dict, Optional

from pydantic import BaseModel

from patientshield.core.documents.models import DOCUMENT_TYPE_LABELS, DocumentInfo, DocumentType
from patientshield.core.documents.parsing import DocumentError, ParsedDocument, parse_document

RETENTION_NOTICE = (
    "Your file was processed in memory for this request only. PatientShield did not save it, log its contents, "
    "or send it to any other service. Closing or clearing this page removes it from your browser."
)

Extractor = Callable[[ParsedDocument, DocumentInfo], BaseModel]
_EXTRACTORS: Dict[str, Extractor] = {}


def register_extractor(doc_type: DocumentType, extractor: Extractor) -> None:
    _EXTRACTORS[doc_type] = extractor


def supported_types() -> list:
    return sorted(_EXTRACTORS)


def process(name: str, data: bytes, doc_type: DocumentType, synthetic: bool = False, sample_id: Optional[str] = None) -> BaseModel:
    extractor = _EXTRACTORS.get(doc_type)
    if extractor is None:
        label = DOCUMENT_TYPE_LABELS.get(doc_type, "this kind of document")
        raise DocumentError("not_available", f"Reading {label} isn't available yet. It's coming soon.", status=422)
    doc = parse_document(name, data)
    info = DocumentInfo(
        name=doc.name,
        doc_type=doc_type,
        kind=doc.kind,  # type: ignore[arg-type]
        page_count=len(doc.pages),
        size_bytes=doc.size_bytes,
        synthetic=synthetic,
        sample_id=sample_id,
    )
    return extractor(doc, info)
