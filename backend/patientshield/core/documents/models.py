"""Models shared by every document type."""

from typing import Dict, Literal, Optional

from pydantic import BaseModel

DocumentType = Literal["denial", "eob", "bill"]

DOCUMENT_TYPE_LABELS: Dict[str, str] = {
    "denial": "a denial letter",
    "eob": "an Explanation of Benefits",
    "bill": "a medical bill",
}


class Page(BaseModel):
    number: int
    text: str


class DocumentInfo(BaseModel):
    name: str
    doc_type: DocumentType = "denial"
    kind: Literal["pdf", "text"]
    page_count: int
    size_bytes: int
    synthetic: bool
    sample_id: Optional[str] = None
