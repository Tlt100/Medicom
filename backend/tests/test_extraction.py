"""Extraction engine: segmentation offsets, field extraction, citations and failure handling."""

import io

import pytest
from pypdf import PdfWriter

from patientshield.core.citations import Citation, CitationError
from patientshield.core.citations import check_document_citations as _check
from patientshield.core.documents import parsing as documents
from patientshield.core.documents.parsing import DocumentError, normalize_text, parse_document
from patientshield.core.documents.pdfgen import render_pdf
from patientshield.core.documents.segment import segment_document, segment_page
from patientshield.features.denials.extraction import extract
from patientshield.features.denials.samples import SAMPLES, SAMPLES_BY_ID, page_texts


def run(sample_id: str):
    s = SAMPLES_BY_ID[sample_id]
    return extract(s.filename, render_pdf(s), synthetic=True, sample_id=s.id)


def fields(result):
    return {f.key: f for f in result.fields}


# ---------------------------------------------------------------- citations: the core guarantee


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda s: s.id)
def test_every_citation_is_the_exact_page_text(sample):
    result = extract(sample.filename, render_pdf(sample), synthetic=True)
    pages = [p.text for p in result.pages]
    citations = [c for f in result.fields for c in f.citations] + [c for s in result.signals for c in s.citations]
    assert citations, "every sample should produce at least one citation"
    for c in citations:
        assert pages[c.page - 1][c.start : c.end] == c.quote


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda s: s.id)
def test_found_fields_always_have_citations_and_missing_fields_have_guidance(sample):
    for f in extract(sample.filename, render_pdf(sample)).fields:
        if f.status == "found":
            assert f.value and f.citations, f.key
        else:
            assert f.value is None and f.note, f.key


def test_citation_check_rejects_a_tampered_quote():
    with pytest.raises(CitationError):
        _check(["Your claim was denied."], [Citation(page=1, start=0, end=10, quote="Your clain")])
    with pytest.raises(CitationError):
        _check(["Only one page"], [Citation(page=2, start=0, end=4, quote="Only")])


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda s: s.id)
def test_segmentation_preserves_offsets(sample):
    pages = parse_document(sample.filename, render_pdf(sample)).pages
    passages = segment_document(pages)
    assert passages
    for p in passages:
        assert pages[p.page - 1][p.start : p.end] == p.text


def test_segmentation_joins_wrapped_lines_and_keeps_labels_separate():
    text = (
        "Pinebrook Health Plan\n"
        "Claim Number: CLM-1\n"
        "Your request has been denied because the service is not medically necessary under our policy for\n"
        "imaging. You may appeal.\n"
    )
    kinds = [(p.kind, p.flat) for p in segment_page(1, text)]
    assert ("heading", "Pinebrook Health Plan") in kinds
    assert ("label", "Claim Number: CLM-1") in kinds
    assert any(k == "sentence" and t.endswith("for imaging.") for k, t in kinds)
    assert ("sentence", "You may appeal.") in kinds


def test_sentence_split_respects_abbreviations():
    text = "Send it to P.O. Box 12 by fax. Dr. Placeholder reviewed it. Call 8 a.m. to 6 p.m. Monday."
    sentences = [p.flat for p in segment_page(1, text)]
    assert sentences[0] == "Send it to P.O. Box 12 by fax."
    assert sentences[1] == "Dr. Placeholder reviewed it."


# ---------------------------------------------------------------- per-letter expectations


def test_nj_fully_insured_letter():
    f = fields(run("nj-prior-auth-mri"))
    assert "not medically necessary" in f["denial_reason"].value
    assert f["denial_reason"].citations[0].page == 1
    assert f["appeal_deadline"].normalized == "180 calendar days"
    assert f["appeal_deadline"].citations[0].page == 2
    assert f["external_review_deadline"].normalized == "4 months"
    assert f["letter_date"].normalized == "2026-09-15"
    assert f["insurer_name"].value == "Pinebrook Health Plan"
    assert f["plan_name"].value.startswith("Pinebrook Gold PPO")
    assert "Claim Number: CLM-2026-0915-3382" in f["reference_numbers"].values
    assert any("Appeals Unit" in v for v in f["appeal_instructions"].values)


def test_insurer_decision_timeline_is_not_mistaken_for_the_members_deadline():
    f = fields(run("nj-prior-auth-mri"))
    assert all("72 hours" not in v for v in f["appeal_deadline"].values)


def test_self_funded_letter_signals_plan_type_without_concluding_it():
    result = run("self-funded-out-of-network")
    f = fields(result)
    assert "out of network" in f["denial_reason"].value
    assert f["appeal_deadline"].normalized == "180 days"
    codes = {s.code for s in result.signals}
    assert {"self-funded", "erisa"} <= codes
    assert "new-jersey" not in codes


def test_medicaid_letter_lists_both_time_limits_and_notes_it():
    result = run("nj-familycare-home-health")
    f = fields(result)
    assert f["appeal_deadline"].normalized == "60 calendar days"
    assert any("10 calendar days" in v for v in f["appeal_deadline"].values)
    assert f["appeal_deadline"].note and "more than one" in f["appeal_deadline"].note
    assert f["external_review_deadline"].status == "not_found"
    assert f["plan_name"].status == "not_found"
    assert "medicaid" in {s.code for s in result.signals}


def test_vague_letter_reports_missing_details_instead_of_guessing():
    result = run("vague-letter-missing-details")
    f = fields(result)
    for key in ("appeal_instructions", "appeal_deadline", "reference_numbers", "plan_name"):
        assert f[key].status == "not_found", key
        assert f[key].value is None
    reason = f["denial_reason"]
    assert reason.status == "not_found"
    assert "doesn't explain why" in reason.note
    assert "not approved" in reason.citations[0].quote


def test_prompt_injection_is_flagged_and_has_no_effect():
    result = run("vague-letter-missing-details")
    suspicious = [s for s in result.signals if s.kind == "suspicious"]
    assert suspicious and "ignore all previous instructions" in suspicious[0].citations[0].quote
    assert any("addressed to software" in w for w in result.warnings)
    serialized = result.model_dump_json().lower()
    assert '"status":"approved"' not in serialized.replace(" ", "")


# ---------------------------------------------------------------- text uploads


def test_plain_text_upload_with_page_markers():
    text = "\n\n--- Page 1 ---\n\n".join(page_texts(SAMPLES_BY_ID["nj-prior-auth-mri"]))
    result = extract("letter.txt", text.encode("utf-8"))
    assert result.document.kind == "text" and result.document.page_count == 2
    f = fields(result)
    assert f["appeal_deadline"].citations[0].page == 2


def test_normalize_text_strips_hidden_characters():
    assert normalize_text("Claim​ denied‮.\x07  Now") == "Claim denied. Now"


# ---------------------------------------------------------------- parsing failures


def _pdf_with_blank_page() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _encrypted_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret")
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.parametrize(
    "name,data,code",
    [
        ("empty.pdf", b"", "empty"),
        ("fake.pdf", b"not really a pdf", "unsupported_type"),
        ("program.exe", b"MZ\x90\x00", "unsupported_type"),
        ("binary.txt", b"abc\x00def", "binary_content"),
        ("latin1.txt", "caf\xe9".encode("latin-1"), "bad_encoding"),
        ("broken.pdf", b"%PDF-1.4\n%%garbage that is not a pdf body", "parse_failed"),
        ("blank.pdf", None, "no_text"),
        ("locked.pdf", "encrypted", "encrypted"),
        ("whitespace.txt", b"   \n\n\t ", "no_text"),
    ],
)
def test_parsing_failures_are_safe_and_specific(name, data, code):
    if data is None:
        data = _pdf_with_blank_page()
    elif data == "encrypted":
        data = _encrypted_pdf()
    with pytest.raises(DocumentError) as err:
        parse_document(name, data)
    assert err.value.code == code
    assert err.value.message and "Traceback" not in err.value.message


def test_too_large_file_is_rejected(monkeypatch):
    monkeypatch.setattr(documents, "MAX_BYTES", 10)
    with pytest.raises(DocumentError) as err:
        parse_document("a.txt", b"x" * 11)
    assert err.value.code == "too_large" and err.value.status == 413


def test_too_many_pages_is_rejected():
    text = "\f".join(f"Page {i} text." for i in range(documents.MAX_PAGES + 1))
    with pytest.raises(DocumentError) as err:
        parse_document("long.txt", text.encode())
    assert err.value.code == "too_many_pages"


def test_file_names_are_sanitized():
    assert documents.safe_name('../../etc/<script>"x".txt') == "....etcscriptx.txt"
    assert documents.safe_name("") == "document"
    assert len(documents.safe_name("a" * 500)) == 120


# ---------------------------------------------------------------- complexity limits (DoS hardening)

import time  # noqa: E402

from hostile_pdfs import single_page, text_ops, xobject_amplified  # noqa: E402


def _timed_parse(data: bytes):
    started = time.perf_counter()
    try:
        parse_document("hostile.pdf", data)
        outcome = "ok"
    except DocumentError as exc:
        outcome = exc.code
    return outcome, time.perf_counter() - started


def test_a_tiny_pdf_describing_a_huge_page_is_rejected_quickly():
    data = single_page(text_ops(10_000))
    assert len(data) < 20_000  # ~10 KB file that used to cost ~30 s of CPU
    outcome, seconds = _timed_parse(data)
    assert outcome == "too_complex"
    assert seconds < 2


def test_form_xobject_amplification_is_counted():
    # 20 text operators inside a form, drawn 500 times = 10,000 operators of work from a few hundred bytes.
    outcome, seconds = _timed_parse(xobject_amplified(inner_ops=20, invocations=500))
    assert outcome == "too_complex" and seconds < 2


def test_deeply_nested_forms_are_rejected():
    outcome, _ = _timed_parse(xobject_amplified(inner_ops=1, invocations=1, depth=documents.MAX_XOBJECT_DEPTH + 1))
    assert outcome == "too_complex"


def test_a_modest_form_xobject_is_still_read():
    outcome, _ = _timed_parse(xobject_amplified(inner_ops=5, invocations=3))
    assert outcome == "ok"


def test_worst_case_just_under_the_limits_stays_well_within_the_time_budget():
    data = single_page(text_ops(documents.MAX_PAGE_CONTENT_BYTES // 240, chars=200))
    outcome, seconds = _timed_parse(data)
    assert outcome == "ok"
    assert seconds < documents.TIME_BUDGET_SECONDS
