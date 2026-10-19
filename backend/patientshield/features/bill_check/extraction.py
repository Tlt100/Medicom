"""EOB and bill extraction: the extractors the core document pipeline calls for doc types "eob" and "bill"."""

from typing import List

from patientshield.core.citations import check_document_citations
from patientshield.core.documents.models import DocumentInfo, Page
from patientshield.core.documents.parsing import ParsedDocument
from patientshield.core.documents.pipeline import RETENTION_NOTICE, register_extractor
from patientshield.features.bill_check.lineitems import read_line_items
from patientshield.features.bill_check.models import DocumentIn, LineItemExtraction, LineItemIn, TotalIn

_LABEL = {"eob": "EOB", "bill": "bill"}


def _extract(doc: ParsedDocument, info: DocumentInfo) -> LineItemExtraction:
    doc_type = info.doc_type
    columns, items, totals, warnings = read_line_items(doc.pages, doc_type, doc_type)
    check_document_citations(doc.pages, [i.citation for i in items] + [t.citation for t in totals])

    label = _LABEL[doc_type]
    if not items:
        warnings.insert(
            0, f"We couldn't find any service lines on this {label}: rows that start with a date of service and show an amount."
        )
    if doc_type == "eob" and items and "patient_owes" not in columns and not any(t.key == "patient_owes" for t in totals):
        warnings.append("We couldn't find how much the EOB says you owe, so the totals can't be compared.")
    if doc_type == "bill" and not any(t.key == "amount_due" for t in totals):
        warnings.append("We couldn't find the amount due on this bill, so the totals can't be compared.")
    if doc.truncated:
        warnings.append("This document was very long, so only the first part was read.")

    return LineItemExtraction(
        document=info,
        pages=[Page(number=i, text=t) for i, t in enumerate(doc.pages, start=1)],
        columns=columns,
        line_items=items,
        totals=totals,
        warnings=warnings,
        retention=RETENTION_NOTICE,
    )


register_extractor("eob", _extract)
register_extractor("bill", _extract)


def to_input(extraction: LineItemExtraction) -> DocumentIn:
    """What the browser sends back for comparison: the values only, no page text."""
    items: List[LineItemIn] = [
        LineItemIn(
            id=i.id,
            service_date=i.service_date,
            code=i.code,
            description=i.description,
            amounts=i.amounts,
            status=i.status,
        )
        for i in extraction.line_items
    ]
    return DocumentIn(line_items=items, totals=[TotalIn(key=t.key, amount_cents=t.amount_cents) for t in extraction.totals])
