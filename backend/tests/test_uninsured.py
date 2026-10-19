"""Uninsured NJ patients: every published number traces to verified source text, and income is never accepted."""

import re

from patientshield.core.sources.service import get_source
from patientshield.features.uninsured.routes import rules
from patientshield.features.uninsured.rules import (
    CHARITY_CARE_BANDS,
    CHARITY_CARE_SOURCE,
    CURRENT_GUIDELINE_YEAR,
    GUIDELINES,
    UNINSURED_CAP_BELOW_PERCENT,
    UNINSURED_CAP_MEDICARE_PERCENT,
    UNINSURED_CAP_SOURCE,
)


def excerpts(*source_ids: str) -> str:
    return " ".join(e.text for sid in source_ids for e in get_source(sid).excerpts)  # type: ignore[union-attr]


def dollars(cents: int) -> str:
    return f"${cents // 100:,}"


def test_guideline_table_follows_its_own_increment():
    g = GUIDELINES[CURRENT_GUIDELINE_YEAR]
    assert g.by_household_size == [g.first_person_cents + n * g.additional_person_cents for n in range(8)]


def test_every_guideline_number_appears_in_the_source():
    g = GUIDELINES[CURRENT_GUIDELINE_YEAR]
    text = excerpts(*g.source_ids)
    for size, cents in enumerate(g.by_household_size, start=1):
        assert f"{size} {dollars(cents)}" in text, size
    assert f"add {dollars(g.additional_person_cents)} for each additional person" in text
    assert "January 13, 2026" in text and g.effective == "2026-01-13"
    assert "48 CONTIGUOUS STATES" in text and g.region == "48 contiguous states and DC"


def test_charity_care_bands_match_the_fact_sheet_exactly():
    table = excerpts(CHARITY_CARE_SOURCE)
    previous = None
    for band in CHARITY_CARE_BANDS:
        if previous is None:
            expected = f"less than or equal to {band.max_percent}% {band.patient_share_percent}%"
        else:
            expected = f"greater than {previous}% but less than or equal to {band.max_percent}% {band.patient_share_percent}%"
        assert expected in table, expected
        previous = band.max_percent
    assert f"greater than {previous}% 100%" in table


def test_uninsured_cap_numbers_match_the_statute_and_stay_flagged_for_review():
    text = excerpts(UNINSURED_CAP_SOURCE)
    assert f"less than {UNINSURED_CAP_BELOW_PERCENT}% of the federal poverty level" in text
    assert f"no greater than {UNINSURED_CAP_MEDICARE_PERCENT}% of the applicable payment rate under the federal Medicare program" in text
    assert get_source(UNINSURED_CAP_SOURCE).verification.value == "needs-review"  # type: ignore[union-attr]


def test_rules_endpoint_serves_versioned_numbers_and_cited_claims(api_client):
    res = api_client.get("/api/uninsured/rules")
    assert res.status_code == 200
    body = res.json()
    assert body["guideline"]["year"] == 2026 and body["guideline"]["first_person_cents"] == 1_596_000
    assert [b["max_percent"] for b in body["charity_care_bands"]] == [200, 225, 250, 275, 300]
    assert body["uninsured_cap"] == {"below_percent": 500, "medicare_percent": 115, "source_id": "nj-pl-2008-c60"}
    assert body["claims"]["nj_uninsured_cap"]["needs_review"] is True
    assert body["claims"]["charity_care_income"]["needs_review"] is False
    assert "not a decision" in body["disclaimer"]


def test_there_is_no_endpoint_that_accepts_income(api_client):
    assert api_client.post("/api/uninsured/rules", json={"income": 50000}).status_code == 405
    paths = api_client.app.openapi()["paths"]
    uninsured = {p: set(ops) for p, ops in paths.items() if p.startswith("/api/uninsured")}
    assert uninsured == {"/api/uninsured/rules": {"get"}}


def test_claims_never_promise_or_accuse():
    text = " ".join(c.text for c in rules().claims.values()) + " " + rules().disclaimer
    assert not re.search(r"illegal|unlawful|overcharg|guarantee|you will (get|receive|qualify)|entitled", text, re.I)
