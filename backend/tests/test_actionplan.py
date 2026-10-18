"""Action plan: deadline math, letter-vs-rule comparisons, plan-specific steps, and safety of wording."""

import datetime as dt

import pytest
from pydantic import ValidationError

from patientshield.core.dates import add_business_days, add_months, parse_duration
from patientshield.features.denials.actionplan.builder import build_plan
from patientshield.features.denials.actionplan.models import PlanRequest

TODAY = dt.date(2026, 10, 17)
NJ = {"coverage_source": "job", "employer_type": "private", "funding": "fully_insured", "issued_state": "nj", "grandfathered": "no"}
SELF_FUNDED = {"coverage_source": "job", "employer_type": "private", "funding": "self_funded", "grandfathered": "no"}


def quote(text, page=1):
    return {"text": text, "page": page}


def stated(text, page=2):
    return {"text": text, "quote": quote(f"You must appeal within {text}.", page)}


def plan(answers, letter=None, situation=None, today=TODAY):
    return build_plan(PlanRequest.model_validate({"answers": answers, "letter": letter or {}, "situation": situation or {}}), today=today)


NJ_LETTER = {
    "letter_date": "2026-09-15",
    "denial_reason": quote("Your request has been denied because the service is not medically necessary."),
    "appeal_instructions": [quote("Send your written appeal to the Appeals Unit.", 2)],
    "appeal_deadline": stated("180 calendar days of the date you receive this notice"),
    "external_review_deadline": stated("4 months of receiving our final internal appeal decision"),
}


# ---------------------------------------------------------------- date math


@pytest.mark.parametrize(
    "start,months,expected",
    [
        (dt.date(2026, 10, 31), 4, dt.date(2027, 2, 28)),
        (dt.date(2027, 10, 31), 4, dt.date(2028, 2, 29)),
        (dt.date(2026, 9, 15), 4, dt.date(2027, 1, 15)),
        (dt.date(2026, 11, 30), 3, dt.date(2027, 2, 28)),
    ],
)
def test_add_months_clamps_to_month_end(start, months, expected):
    assert add_months(start, months) == expected


def test_business_days_skip_weekends():
    assert add_business_days(dt.date(2026, 10, 16), 1) == dt.date(2026, 10, 19)  # Friday + 1 -> Monday
    assert add_business_days(dt.date(2026, 10, 12), 10) == dt.date(2026, 10, 26)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("180 calendar days of the date you receive this notice", (180, "days", "calendar")),
        ("4 months", (4, "months", "calendar")),
        ("10 business days", (10, "days", "business")),
        ("60 (sixty) days from the date on this notice", (60, "days", "calendar")),
        ("1 day", (1, "days", "calendar")),
        ("72 hours", None),
        ("thirty days", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_duration(text, expected):
    assert parse_duration(text) == expected


# ---------------------------------------------------------------- NJ-regulated plan, letter and rule agree


def test_nj_plan_shows_letter_and_rule_deadlines_and_compares_them():
    p = plan(NJ, NJ_LETTER, {"date_received": "2026-09-18", "internal_appeal": "not_yet"})
    by_id = {d.id: d for d in p.deadlines}
    assert by_id["letter-appeal"].date == dt.date(2027, 3, 17)
    assert by_id["letter-appeal"].kind == "letter" and by_id["letter-appeal"].quote.page == 2
    assert by_id["rule-appeal"].date == dt.date(2027, 3, 17)
    assert by_id["rule-appeal"].claim.id == "internal_appeal_window"
    assert by_id["rule-appeal"].days_left == 151 and not by_id["rule-appeal"].passed
    assert p.plan_around.startswith("Plan around March 17, 2027")

    rows = {c.topic: c for c in p.comparisons}
    deadline_row = rows["Deadline for the first appeal"]
    assert deadline_row.letter.page == 2
    assert [r.id for r in deadline_row.rules] == ["internal_appeal_window"]
    assert "at least as long" in deadline_row.note
    assert {r.id for r in rows["If the first appeal is denied"].rules} >= {"ihcap_internal_first", "ihcap_timing"}

    steps = [s.id for s in p.steps]
    assert steps.index("file-appeal") < steps.index("next-stage") < steps.index("records")
    assert any("IHCAP" in s.title for s in p.steps)
    assert [c.phone for c in p.contacts] == ["1-888-393-1062", "1-800-446-7467"]


def test_letter_with_less_time_than_the_rule_is_flagged_neutrally_and_planned_around():
    letter = dict(NJ_LETTER, appeal_deadline=stated("30 days of the date you receive this notice"))
    p = plan(NJ, letter, {"date_received": "2026-10-01"})
    row = next(c for c in p.comparisons if c.topic == "Deadline for the first appeal")
    assert "less time than the general rule" in row.note
    assert "plan around the letter’s earlier date" in row.note.lower()
    assert p.plan_around.startswith("Plan around October 31, 2026")
    text = p.model_dump_json().lower()
    for word in ("violat", "illegal", "unlawful", "you will win"):
        assert word not in text


def test_counts_from_the_printed_date_when_received_date_is_missing_and_says_so():
    p = plan(NJ, NJ_LETTER, {})
    assert next(d for d in p.deadlines if d.id == "rule-appeal").date == dt.date(2027, 3, 14)
    assert any("printed on the letter" in u for u in p.uncertainties)


def test_no_dates_means_no_calendar_deadlines_and_a_prompt_to_add_one():
    letter = {k: v for k, v in NJ_LETTER.items() if k != "letter_date"}
    p = plan(NJ, letter, {})
    assert p.deadlines == [] and p.plan_around is None
    assert any("Add the date you received" in u for u in p.uncertainties)


def test_passed_deadlines_are_marked_and_explained():
    p = plan(NJ, NJ_LETTER, {"date_received": "2025-01-02"}, today=TODAY)
    assert all(d.passed for d in p.deadlines)
    assert "have passed" in p.plan_around and "Only the plan or a regulator can say" in p.plan_around


def test_after_internal_appeal_decision_external_review_deadlines_are_computed():
    p = plan(NJ, NJ_LETTER, {"date_received": "2026-05-01", "internal_appeal": "decided", "final_decision_date": "2026-09-30"})
    by_id = {d.id: d for d in p.deadlines}
    assert "rule-appeal" not in by_id and "letter-appeal" not in by_id
    assert by_id["rule-external"].date == dt.date(2027, 1, 30)
    assert "IHCAP page doesn’t state" in by_id["rule-external"].note
    assert by_id["letter-external"].date == dt.date(2027, 1, 30)
    assert next(s for s in p.steps if s.id == "next-stage").title.startswith("Request independent external review")


def test_decided_without_a_date_asks_for_it():
    p = plan(NJ, NJ_LETTER, {"internal_appeal": "decided"})
    assert any("final appeal decision" in u for u in p.uncertainties)


# ---------------------------------------------------------------- other plan types


def test_self_funded_plan_uses_federal_rules_and_department_of_labor():
    p = plan(SELF_FUNDED, NJ_LETTER, {"date_received": "2026-09-18"})
    assert next(d for d in p.deadlines if d.id == "rule-appeal").claim.id == "erisa_appeal_window"
    nxt = next(s for s in p.steps if s.id == "next-stage")
    assert {c.id for c in nxt.claims} >= {"erisa_external", "ihcap_scope"}
    assert [c.name for c in p.contacts] == ["U.S. Department of Labor, Employee Benefits Security Administration"]


def test_medicaid_counts_from_the_notice_date_and_surfaces_the_shorter_limit():
    letter = {
        "letter_date": "2026-10-10",
        "denial_reason": quote("Our review found that the requested number of hours is more than what is needed."),
        "appeal_deadline": stated("60 calendar days from the date on this notice", 1),
        "other_time_limits": [stated("10 calendar days of the date on this notice", 1)],
    }
    p = plan({"coverage_source": "medicaid"}, letter, {"date_received": "2026-10-14"})
    by_id = {d.id: d for d in p.deadlines}
    assert by_id["letter-appeal"].date == dt.date(2026, 12, 9)  # from the notice date, not receipt
    assert by_id["rule-appeal"].date == dt.date(2026, 12, 9)
    assert by_id["letter-other-0"].date == dt.date(2026, 10, 20)
    assert p.plan_around.startswith("Plan around October 20, 2026")
    nxt = next(s for s in p.steps if s.id == "next-stage")
    assert [c.needs_review for c in nxt.claims] == [True]
    assert any("services will continue" in q or "services continue" in q for q in p.questions)


def test_medicare_advantage_vs_original():
    ma = plan({"coverage_source": "medicare", "medicare_kind": "advantage"}, NJ_LETTER, {"date_received": "2026-09-18"})
    assert next(d for d in ma.deadlines if d.id == "rule-appeal").claim.id == "ma_reconsideration_60"
    original = plan({"coverage_source": "medicare", "medicare_kind": "original"}, NJ_LETTER, {"date_received": "2026-09-18"})
    assert "rule-appeal" not in {d.id for d in original.deadlines}
    assert next(s for s in original.steps if s.id == "file-appeal").title == "Follow the appeal instructions on your notice"


def test_unknown_plan_gets_no_rule_deadlines_and_starts_with_confirming_plan_type():
    p = plan({"coverage_source": "unsure"}, NJ_LETTER, {"date_received": "2026-09-18"})
    assert {d.kind for d in p.deadlines} == {"letter"}
    assert p.steps[0].id == "confirm-plan"
    assert "file-appeal" not in {s.id for s in p.steps}
    row = next(c for c in p.comparisons if c.topic == "Deadline for the first appeal")
    assert row.rules == [] and "Confirm your plan type" in row.rules_summary


# ---------------------------------------------------------------- letter gaps and urgency


def test_missing_reason_becomes_a_step_and_a_question():
    letter = {"letter_date": "2026-07-30", "denial_statement": quote("Your claim for services on July 2, 2026 was not approved.")}
    p = plan(NJ, letter, {})
    step = next(s for s in p.steps if s.id == "ask-reason")
    assert step.quote.text.endswith("was not approved.")
    assert p.questions[0].startswith("What is the specific reason")
    row = p.comparisons[0]
    assert row.letter_status == "not_found" and row.letter.text.endswith("was not approved.")


def test_urgent_situation_puts_expedited_appeal_first_with_the_right_citation():
    job = plan(NJ, NJ_LETTER, {"urgent": "yes"})
    assert job.steps[0].id == "urgent" and [c.id for c in job.steps[0].claims] == ["urgent_72h"]
    medicaid = plan({"coverage_source": "medicaid"}, {}, {"urgent": "yes"})
    assert medicaid.steps[0].id == "urgent" and medicaid.steps[0].claims == []


def test_every_cited_claim_has_sources():
    p = plan(NJ, NJ_LETTER, {"date_received": "2026-09-18", "urgent": "yes"})
    claims = [c for s in p.steps for c in s.claims] + [r for row in p.comparisons for r in row.rules]
    assert claims and all(c.sources for c in claims)


# ---------------------------------------------------------------- input validation and API


@pytest.mark.parametrize(
    "body",
    [
        {"answers": NJ, "situation": {"date_received": "1990-01-01"}},
        {"answers": NJ, "situation": {"urgent": "maybe"}},
        {"answers": NJ, "letter": {"denial_reason": {"text": "x" * 601, "page": 1}}},
        {"answers": NJ, "letter": {"denial_reason": {"text": "ok", "page": 99}}},
        {"answers": NJ, "letter": {"unexpected": True}},
    ],
)
def test_request_validation(body):
    with pytest.raises(ValidationError):
        PlanRequest.model_validate(body)


def test_plan_endpoint(client):
    res = client.post("/api/plan", json={"answers": NJ, "letter": NJ_LETTER, "situation": {"date_received": "2026-09-18"}})
    assert res.status_code == 200
    body = res.json()
    assert body["plan_type"] == "nj-regulated" and body["deadlines"] and body["steps"]
    assert res.headers["cache-control"] == "no-store"


def test_plan_endpoint_rejects_off_path_answers_without_echoing_them(client):
    res = client.post("/api/plan", json={"answers": {"coverage_source": "<script>"}})
    assert res.status_code == 422 and "<script>" not in res.text


def test_plan_endpoint_uses_the_clients_local_date_only_within_a_day(client):
    server_today = dt.date.today()
    base = {"answers": NJ, "letter": NJ_LETTER, "situation": {"date_received": "2026-09-18"}}
    for offset, honored in [(-1, True), (1, True), (5, False)]:
        sent = server_today + dt.timedelta(days=offset)
        body = client.post("/api/plan", json={**base, "today": sent.isoformat()}).json()
        assert body["today"] == (sent if honored else server_today).isoformat()
