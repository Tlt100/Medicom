"""Bill check: reading EOBs and bills, line-item matching, flags, and the API."""

import re
from urllib.parse import quote

import pytest

from patientshield.core.claims import CLAIMS
from patientshield.core.documents.pdfgen import render_pdf
from patientshield.core.documents.pipeline import process
from patientshield.features.bill_check.compare import compare, match_lines, money
from patientshield.features.bill_check.extraction import to_input
from patientshield.features.bill_check.lineitems import cents, header_columns, read_line_items
from patientshield.features.bill_check.models import DocumentIn, LineItemIn, TotalIn
from patientshield.features.bill_check.samples import SAMPLE_PAIRS, SAMPLE_PAIRS_BY_ID


def item(id, date="2026-09-02", code=None, desc="Office visit", billed=None, owes=None, status="listed"):
    amounts = {}
    if billed is not None:
        amounts["billed"] = billed
    if owes is not None:
        amounts["patient_owes"] = owes
    return LineItemIn(id=id, service_date=date, code=code, description=desc, amounts=amounts, status=status)


def doc(items, **totals):
    return DocumentIn(line_items=items, totals=[TotalIn(key=k, amount_cents=v) for k, v in totals.items()])


def run_pair(pair_id):
    pair = SAMPLE_PAIRS_BY_ID[pair_id]
    eob = process(pair.eob.filename, render_pdf(pair.eob), "eob", synthetic=True)
    bill = process(pair.bill.filename, render_pdf(pair.bill), "bill", synthetic=True)
    return eob, bill, compare(to_input(eob), to_input(bill))


# ---------------------------------------------------------------- reading amounts and columns


@pytest.mark.parametrize(
    "token,expected",
    [("$1,450.00", 145000), ("64.00", 6400), ("-$117.28", -11728), ("$-5.00", -500), ("($12.50)", -1250), ("$0.00", 0)],
)
def test_money_is_read_as_exact_cents(token, expected):
    assert cents(token) == expected


def test_money_formats_back_to_dollars():
    assert money(251360) == "$2,513.60" and money(-500) == "-$5.00" and money(4) == "$0.04"


def test_header_words_map_to_columns_in_order():
    assert header_columns("Date Service Code Billed Allowed Plan paid You owe") == ["billed", "allowed", "plan_paid", "patient_owes"]
    assert header_columns("Date of service | Provider charges | Deductible | Coinsurance | Your share") == [
        "billed",
        "deductible",
        "coinsurance",
        "patient_owes",
    ]
    assert header_columns("Date Code Description Charges") == ["billed"]


def test_rows_are_read_with_date_code_description_and_cited_line():
    page = "Date Service Code Billed Allowed Plan paid You owe\n09/02/2026 Office visit 99214 $210.00 $128.40 $102.72 $25.68\n"
    columns, items, totals, warnings = read_line_items([page], "eob", "eob")
    (row,) = items
    assert (row.id, row.service_date, row.code, row.description) == ("eob-1", "2026-09-02", "99214", "Office visit")
    assert row.amounts == {"billed": 21000, "allowed": 12840, "plan_paid": 10272, "patient_owes": 2568}
    assert page[row.citation.start : row.citation.end] == row.citation.quote == page.splitlines()[1]
    assert warnings == []


def test_amounts_are_not_guessed_when_columns_dont_line_up():
    page = "Date Service Code Billed Allowed Plan paid You owe\n09/02/2026 Office visit 99214 $210.00 $25.68\n"
    _, items, _, warnings = read_line_items([page], "eob", "eob")
    assert items[0].amounts == {}
    assert "couldn't tell which column" in warnings[0]


def test_a_bill_row_with_one_amount_is_its_charge_even_without_a_header():
    _, items, _, _ = read_line_items(["09/02/2026 99214 Office visit $210.00"], "bill", "bill")
    assert items[0].amounts == {"billed": 21000}


def test_prose_is_not_mistaken_for_a_table_header():
    page = (
        "Date Code Description Charges\n"
        "Your share of the cost depends on your deductible and coinsurance, as described in your plan documents.\n"
        "09/02/2026 99214 Office visit $210.00\n"
    )
    columns, items, _, _ = read_line_items([page], "bill", "bill")
    assert columns == ["billed"] and items[0].amounts == {"billed": 21000}


def test_denied_rows_and_labelled_totals():
    page = (
        "Date Service Code Billed Allowed Plan paid You owe\n"
        "08/14/2026 Wound care supplies A6216 $95.00 $0.00 $0.00 $95.00 DENIED - not covered\n"
        "Total you owe: $95.00\nAmount due: $95.00\n"
    )
    _, items, totals, _ = read_line_items([page], "eob", "eob")
    assert items[0].status == "denied" and items[0].code == "A6216"
    assert {t.key: t.amount_cents for t in totals} == {"patient_owes": 9500, "amount_due": 9500}


def test_impossible_dates_are_not_invented():
    _, items, _, _ = read_line_items(["13/45/2026 99214 Office visit $210.00"], "bill", "bill")
    assert items[0].service_date is None


# ---------------------------------------------------------------- line-item matching


def test_matches_on_code_and_date_and_explains_why():
    (m,) = match_lines([item("bill-1", code="99214", billed=21000)], [item("eob-1", code="99214", billed=21000)])
    assert (m.bill_item_id, m.eob_item_id) == ("bill-1", "eob-1")
    assert m.matched_on == ["date", "code", "charge", "description"]


def test_different_dates_never_match():
    assert match_lines([item("bill-1", code="99214")], [item("eob-1", date="2026-09-03", code="99214")]) == []


def test_different_codes_never_match_even_with_the_same_charge():
    assert match_lines([item("bill-1", code="99214", billed=100)], [item("eob-1", code="99213", billed=100)]) == []


def test_lines_without_codes_match_on_charge_or_similar_description():
    bill = [item("bill-1", desc="Ambulance transport", billed=90000), item("bill-2", desc="Blood draw venipuncture", billed=2500)]
    eob = [item("eob-1", desc="Venipuncture blood draw", billed=3000), item("eob-2", desc="Transport", billed=90000)]
    pairs = {(m.bill_item_id, m.eob_item_id) for m in match_lines(bill, eob)}
    assert pairs == {("bill-1", "eob-2"), ("bill-2", "eob-1")}


def test_a_date_alone_is_not_a_match():
    assert match_lines([item("bill-1", desc="Visit", billed=100)], [item("eob-1", desc="Imaging", billed=200)]) == []


def test_matching_is_one_to_one_and_prefers_the_code():
    bill = [item("bill-1", code="99214", billed=21000)]
    eob = [item("eob-1", code=None, billed=21000), item("eob-2", code="99214", billed=19000)]
    (m,) = match_lines(bill, eob)
    assert m.eob_item_id == "eob-2"


def test_two_units_listed_on_both_documents_are_not_flagged():
    bill = [item("bill-1", code="97110", billed=6000), item("bill-2", code="97110", billed=6000)]
    eob = [item("eob-1", code="97110", billed=6000), item("eob-2", code="97110", billed=6000)]
    result = compare(doc(eob), doc(bill))
    assert len(result.matches) == 2 and result.flags == []


# ---------------------------------------------------------------- flags and totals


def kinds(result):
    return [f.kind for f in result.flags]


def test_bill_above_what_the_eob_says_you_owe_is_worth_asking_about():
    result = compare(
        doc([item("eob-1", code="99214", billed=100, owes=20)], patient_owes=20),
        doc([item("bill-1", code="99214", billed=100)], amount_due=80),
    )
    assert kinds(result) == ["amount_due_exceeds_eob", "surprise_bill_context"]
    exceeds = result.flags[0]
    assert exceeds.level == "ask" and "$0.80" in exceeds.detail and "$0.20" in exceeds.detail and "$0.60" in exceeds.detail
    assert [c.id for c in exceeds.claims] == ["bill_not_above_eob", "in_network_no_balance_bill"]


def test_bill_below_the_eob_amount_is_explained_not_flagged_as_a_problem():
    result = compare(doc([item("eob-1", code="99214", owes=2500)]), doc([item("bill-1", code="99214")], amount_due=0))
    assert kinds(result) == ["amount_due_below_eob"]
    assert result.flags[0].level == "info" and result.eob_patient_owes_cents == 2500  # summed from the lines


def test_matching_totals_raise_nothing():
    result = compare(doc([item("eob-1", code="99214", owes=2500)], patient_owes=2500), doc([item("bill-1", code="99214")], amount_due=2500))
    assert result.flags == []


def test_totals_are_not_compared_when_either_is_missing():
    result = compare(doc([item("eob-1", code="99214")]), doc([item("bill-1", code="99214")], amount_due=99999))
    assert result.eob_patient_owes_cents is None and result.flags == []


def test_a_bill_without_service_lines_suggests_asking_for_an_itemized_bill():
    result = compare(doc([item("eob-1", code="99214")]), doc([], amount_due=500))
    assert kinds(result)[0] == "no_line_items" and result.flags[0].claims[0].id == "ask_itemized_bill"


@pytest.mark.parametrize(
    "pair_id,expected",
    [
        ("clean-office-visit", []),
        ("imaging-balance-and-repeat", ["possible_duplicate", "amount_due_exceeds_eob", "surprise_bill_context"]),
        ("er-visit-differences", ["charge_differs", "not_on_eob", "amount_due_exceeds_eob", "denied_on_eob", "surprise_bill_context"]),
    ],
)
def test_sample_pairs_raise_exactly_the_expected_flags(pair_id, expected):
    _, _, result = run_pair(pair_id)
    assert kinds(result) == expected


def test_er_sample_points_each_flag_at_the_right_lines():
    _, bill, result = run_pair("er-visit-differences")
    by_kind = {f.kind: f for f in result.flags}
    assert by_kind["charge_differs"].bill_item_ids == ["bill-2"] and by_kind["charge_differs"].eob_item_ids == ["eob-2"]
    assert "$2,250.00" in by_kind["charge_differs"].detail and "$2,100.00" in by_kind["charge_differs"].detail
    missing = next(i for i in bill.line_items if i.id == by_kind["not_on_eob"].bill_item_ids[0])
    assert missing.code == "J1885"
    assert by_kind["denied_on_eob"].eob_item_ids == ["eob-3"]
    assert "Part of the difference may be the charges that aren’t on this EOB." in by_kind["amount_due_exceeds_eob"].detail


def test_sample_documents_add_up():
    """The synthetic numbers are internally consistent, so the demo isn't comparing nonsense."""
    for pair in SAMPLE_PAIRS:
        eob, bill, result = run_pair(pair.id)
        assert sum(i.amounts["patient_owes"] for i in eob.line_items) == result.eob_patient_owes_cents
        t = {x.key: x.amount_cents for x in bill.totals}
        assert sum(i.amounts["billed"] for i in bill.line_items) == t["total_charges"]
        assert t["total_charges"] + t["insurance_paid"] + t.get("adjustments", 0) == t["amount_due"]
        assert not eob.warnings and not bill.warnings


BANNED = re.compile(r"overcharg|illegal|unlawful|fraud|violat|\berror|mistake|scam|ripped|\bwrong\b|owed to you|guarantee", re.I)


def test_flags_say_worth_asking_and_never_accuse():
    for pair in SAMPLE_PAIRS:
        _, _, result = run_pair(pair.id)
        for f in result.flags:
            assert not BANNED.search(f.title + " " + f.detail), (f.kind, f.title)


def test_every_flag_is_cited_or_marked_practical():
    for pair in SAMPLE_PAIRS:
        _, _, result = run_pair(pair.id)
        for f in result.flags:
            assert f.claims or f.practical, f.kind
            assert all(c.id in CLAIMS and c.sources for c in f.claims)
        assert result.next_steps and "not findings that anything is wrong" in result.disclaimer


# ---------------------------------------------------------------- API


def test_samples_list_and_run(api_client):
    listed = api_client.get("/api/bill-check/samples").json()
    assert [s["id"] for s in listed] == [p.id for p in SAMPLE_PAIRS]
    res = api_client.post("/api/bill-check/samples/er-visit-differences")
    assert res.status_code == 200
    body = res.json()
    assert body["eob"]["document"]["doc_type"] == "eob" and body["bill"]["document"]["doc_type"] == "bill"
    assert body["eob"]["document"]["synthetic"] is True
    assert "SYNTHETIC SAMPLE - NOT A REAL BILL OR EOB" in body["bill"]["pages"][0]["text"]


def test_sample_pdfs_download_and_unknown_samples_404(api_client):
    res = api_client.get("/api/bill-check/samples/clean-office-visit/eob.pdf")
    assert res.status_code == 200 and res.headers["content-type"] == "application/pdf" and res.content.startswith(b"%PDF-")
    assert api_client.get("/api/bill-check/samples/clean-office-visit/letter.pdf").status_code == 422
    assert api_client.post("/api/bill-check/samples/not-a-sample").status_code == 404


def test_uploads_go_through_the_shared_pipeline_with_a_document_type(api_client):
    text = "Date Code Description Charges\n09/02/2026 99214 Office visit $210.00\nAmount due: $25.68\n"
    res = api_client.post("/api/extract", content=text.encode(), headers={"X-File-Name": quote("bill.txt"), "X-Document-Type": "bill"})
    assert res.status_code == 200
    body = res.json()
    assert body["document"]["doc_type"] == "bill" and body["line_items"][0]["amounts"] == {"billed": 21000}
    assert body["totals"][0]["key"] == "amount_due"


def test_an_unreadable_upload_says_what_was_missing(api_client):
    res = api_client.post(
        "/api/extract", content=b"Thank you for your payment.", headers={"X-File-Name": "x.txt", "X-Document-Type": "eob"}
    )
    assert res.status_code == 200 and "couldn't find any service lines" in res.json()["warnings"][0]


def _compare_body(**overrides):
    body = {
        "eob": {
            "line_items": [
                {"id": "eob-1", "service_date": "2026-09-02", "code": "99214", "description": "Visit", "amounts": {"patient_owes": 2000}}
            ],
            "totals": [],
        },
        "bill": {
            "line_items": [
                {"id": "bill-1", "service_date": "2026-09-02", "code": "99214", "description": "Visit", "amounts": {"billed": 9000}}
            ],
            "totals": [{"key": "amount_due", "amount_cents": 9000}],
        },
    }
    body.update(overrides)
    return body


def test_compare_endpoint(api_client):
    res = api_client.post("/api/bill-check/compare", json=_compare_body())
    assert res.status_code == 200
    assert [f["kind"] for f in res.json()["flags"]] == ["amount_due_exceeds_eob", "surprise_bill_context"]


@pytest.mark.parametrize(
    "bad",
    [
        {"eob": {"line_items": [], "totals": [], "names": "Riley"}},  # extra fields, such as identifiers, are refused
        {"eob": {"line_items": [{"id": "x; drop", "description": "Visit"}], "totals": []}},
        {"eob": {"line_items": [{"id": "eob-1", "description": "Visit", "amounts": {"billed": 10**15}}], "totals": []}},
        {"eob": {"line_items": [{"id": "eob-1", "description": "Visit", "amounts": {"secret": 1}}], "totals": []}},
        {"eob": {"line_items": [{"id": f"eob-{n}", "description": "Visit"} for n in range(201)], "totals": []}},
    ],
)
def test_compare_rejects_unexpected_input_without_echoing_it(api_client, bad):
    res = api_client.post("/api/bill-check/compare", json=_compare_body(**bad))
    assert res.status_code == 422
    assert "Riley" not in res.text and "drop" not in res.text
