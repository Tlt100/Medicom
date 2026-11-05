"""Ordinary text PDFs from real-world producers must be read, not refused by the DoS limits."""

import io
import time

import pytest
from hostile_pdfs import multi_page, per_glyph_text, text_ops
from pypdf import PdfReader, PdfWriter

from patientshield.core.documents import parsing as documents
from patientshield.core.documents.parsing import DocumentError, parse_document
from patientshield.core.documents.pdfgen import render_pdf
from patientshield.features.denials.samples import SAMPLES

LETTER = SAMPLES[0]


def _restricted_copy(data: bytes, algorithm: str) -> bytes:
    """Encrypted with an empty open password and an owner password, the way statements block printing or editing."""
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(data)))
    writer.encrypt(user_password="", owner_password="owner-only", algorithm=algorithm, permissions_flag=0)  # noqa: S106 - test fixture
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.parametrize("algorithm", ["RC4-128", "AES-128", "AES-256"])
def test_pdfs_encrypted_only_to_restrict_printing_are_read(algorithm):
    original = render_pdf(LETTER)
    restricted = _restricted_copy(original, algorithm)
    assert PdfReader(io.BytesIO(restricted)).is_encrypted
    assert parse_document("statement.pdf", restricted).pages == parse_document("letter.pdf", original).pages


def test_pdfs_that_need_a_password_to_open_are_still_refused():
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(render_pdf(LETTER))))
    writer.encrypt(user_password="secret", owner_password="owner", algorithm="AES-256")  # noqa: S106 - test fixture
    buf = io.BytesIO()
    writer.write(buf)
    with pytest.raises(DocumentError) as err:
        parse_document("locked.pdf", buf.getvalue())
    assert err.value.code == "encrypted"


def test_bytes_before_the_pdf_header_are_tolerated():
    original = render_pdf(LETTER)
    shifted = b"\r\n\xef\xbb\xbfjunk from an email gateway\r\n" + original
    assert parse_document("forwarded.pdf", shifted).pages == parse_document("letter.pdf", original).pages


def test_a_header_beyond_the_allowed_window_is_not_a_pdf():
    with pytest.raises(DocumentError) as err:
        parse_document("odd.pdf", b"x" * documents.PDF_HEADER_WINDOW + render_pdf(LETTER))
    assert err.value.code == "unsupported_type"


def test_one_operator_per_character_pdfs_are_read():
    line = "Your claim for an MRI of the lumbar spine was denied as not medically necessary. "
    text = (line * 60).strip()  # ~4,900 characters: a full, dense page
    pages = parse_document("glyphs.pdf", multi_page([per_glyph_text(text)] * 3)).pages
    assert len(pages) == 3
    # Separately placed letters can come back with extra spaces; the words themselves must all be there.
    assert all("notmedicallynecessary" in "".join(p.split()) for p in pages)


def test_a_long_table_heavy_document_is_read():
    # 20 pages of ~100 KB / ~700 operators each, mostly positioning and cell borders around short values,
    # like a dense EOB. Together they are well over the old document-wide limits (768 KB, 4,500 operators).
    cells = [b"1 0 0 1 %d %d Tm (%05d.00) Tj" % (40 + 60 * (i % 9), 760 - 10 * (i // 9), i) for i in range(700)]
    borders = [b"%d %d 60 10 re S" % (40 + 60 * (i % 9), 758 - 10 * (i // 9)) for i in range(700)] * 3
    page = b"BT /F1 7 Tf\n" + b"\n".join(cells) + b"\nET\n" + b"\n".join(borders)
    assert len(page) > 60_000
    started = time.perf_counter()
    pages = parse_document("eob.pdf", multi_page([page] * 20)).pages
    assert len(pages) == 20 and all(pages)
    assert time.perf_counter() - started < documents.TIME_BUDGET_SECONDS


def test_worst_case_document_just_under_the_limits_stays_within_the_time_budget():
    per_page = documents.MAX_PAGE_CONTENT_BYTES - 4096
    page = text_ops(per_page // 231, chars=200)
    count = documents.MAX_DOC_CONTENT_BYTES // len(page)
    assert len(page) <= documents.MAX_PAGE_CONTENT_BYTES and count * len(page) <= documents.MAX_DOC_CONTENT_BYTES
    started = time.perf_counter()
    try:
        parse_document("heavy.pdf", multi_page([page] * count))
        outcome = "ok"
    except DocumentError as exc:
        outcome = exc.code
    # Either read in full or stopped by the time budget: never an unbounded amount of work.
    assert outcome in {"ok", "too_slow"}
    assert time.perf_counter() - started < documents.TIME_BUDGET_SECONDS + 2


def test_document_wide_limits_still_apply():
    page = text_ops(documents.MAX_PAGE_TEXT_OPS - 10, chars=1)
    count = documents.MAX_DOC_TEXT_OPS // (documents.MAX_PAGE_TEXT_OPS - 10) + 1
    with pytest.raises(DocumentError) as err:
        parse_document("many.pdf", multi_page([page] * min(count, documents.MAX_PAGES)))
    assert err.value.code == "too_complex"
