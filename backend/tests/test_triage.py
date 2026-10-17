"""Plan-type triage: the question tree, classification, cited profiles, and the claims registry."""

import re
from typing import Dict, List

import pytest

from patientshield.claims import CLAIMS
from patientshield.sources.service import get_source
from patientshield.triage.flow import QUESTIONS, START, FlowError, walk
from patientshield.triage.service import classify, suggest, triage

# ---------------------------------------------------------------- claims registry


def test_every_claim_cites_known_sources():
    for claim in CLAIMS.values():
        assert claim.source_ids, claim.id
        for sid in claim.source_ids:
            assert get_source(sid) is not None, f"{claim.id} cites unknown source {sid}"


def test_every_number_in_a_claim_appears_in_its_sources():
    """180 days, 72 hours, phone numbers and dates must be traceable to an excerpt, title or citation of a cited source."""
    for claim in CLAIMS.values():
        haystack = " ".join(
            " ".join([s.title, s.citation or ""] + [e.text for e in s.excerpts]) for s in (get_source(i) for i in claim.source_ids)
        )
        for number in re.findall(r"\d[\d-]*", claim.text):
            assert number in haystack, f"{claim.id}: '{number}' is not in any cited source"


# ---------------------------------------------------------------- the question tree


def all_paths() -> List[Dict[str, str]]:
    paths: List[Dict[str, str]] = []

    def visit(qid: str, answers: Dict[str, str]):
        for option in QUESTIONS[qid].options:
            nxt = dict(answers, **{qid: option.value})
            if option.next is None:
                paths.append(nxt)
            else:
                visit(option.next, nxt)

    visit(START, {})
    return paths


def test_tree_is_well_formed():
    for q in QUESTIONS.values():
        assert len({o.value for o in q.options}) == len(q.options), q.id
        for o in q.options:
            assert o.next is None or o.next in QUESTIONS, f"{q.id}.{o.value} -> {o.next}"


def test_every_path_finishes_and_produces_a_cited_result():
    paths = all_paths()
    assert 15 <= len(paths) <= 60
    seen = set()
    for answers in paths:
        result = triage(answers)
        seen.add(result.plan_type)
        assert result.summary and result.how_to_confirm
        assert len(result.answers) == len(answers)
        for claim in result.claims:
            assert claim.sources
    assert seen == {
        "nj-regulated",
        "marketplace",
        "self-funded",
        "medicaid",
        "medicare",
        "other-state",
        "government-or-religious",
        "unknown",
    }


def test_no_path_asks_more_than_five_questions():
    assert max(len(p) for p in all_paths()) <= 5


@pytest.mark.parametrize(
    "answers,error",
    [
        ({}, "Missing an answer"),
        ({"coverage_source": "job"}, "Missing an answer"),
        ({"coverage_source": "employer"}, "isn’t a valid answer"),
        ({"coverage_source": "medicaid", "funding": "self_funded"}, "don’t belong"),
        ({"coverage_source": "job", "employer_type": "private", "funding": "self_funded"}, "Missing an answer"),
    ],
)
def test_walk_rejects_incomplete_or_invented_answers(answers, error):
    with pytest.raises(FlowError, match=error):
        walk(answers)


# ---------------------------------------------------------------- classification


@pytest.mark.parametrize(
    "answers,plan,confirmed",
    [
        ({"coverage_source": "job", "employer_type": "private", "funding": "self_funded", "grandfathered": "no"}, "self-funded", True),
        ({"coverage_source": "job", "employer_type": "unsure", "funding": "self_funded", "grandfathered": "no"}, "self-funded", False),
        (
            {"coverage_source": "job", "employer_type": "private", "funding": "fully_insured", "issued_state": "nj", "grandfathered": "no"},
            "nj-regulated",
            True,
        ),
        (
            {
                "coverage_source": "job",
                "employer_type": "private",
                "funding": "fully_insured",
                "issued_state": "unsure",
                "grandfathered": "no",
            },
            "nj-regulated",
            False,
        ),
        ({"coverage_source": "job", "employer_type": "private", "funding": "fully_insured", "issued_state": "other"}, "other-state", True),
        ({"coverage_source": "job", "employer_type": "private", "funding": "unsure"}, "unknown", False),
        ({"coverage_source": "job", "employer_type": "government"}, "government-or-religious", True),
        ({"coverage_source": "self_bought", "purchase_channel": "get_covered_nj"}, "marketplace", True),
        ({"coverage_source": "self_bought", "purchase_channel": "insurer_nj"}, "nj-regulated", True),
        ({"coverage_source": "self_bought", "purchase_channel": "other_state"}, "other-state", True),
        ({"coverage_source": "medicaid"}, "medicaid", True),
        ({"coverage_source": "medicare", "medicare_kind": "advantage"}, "medicare", True),
        ({"coverage_source": "medicare", "medicare_kind": "unsure"}, "medicare", False),
        ({"coverage_source": "unsure"}, "unknown", False),
    ],
)
def test_classification(answers, plan, confirmed):
    walk(answers)
    assert classify(answers) == (plan, not confirmed)


# ---------------------------------------------------------------- profiles: what each plan type is told


def claim_ids(answers):
    return [c.id for c in triage(answers).claims]


SELF_FUNDED = {"coverage_source": "job", "employer_type": "private", "funding": "self_funded", "grandfathered": "no"}
NJ = {"coverage_source": "job", "employer_type": "private", "funding": "fully_insured", "issued_state": "nj", "grandfathered": "no"}


def test_self_funded_is_told_ihcap_is_unavailable_and_federal_rules_apply():
    result = triage(SELF_FUNDED)
    assert "IHCAP" in result.summary and "isn’t available" in result.summary
    assert {"erisa_scope", "erisa_appeal_window", "ihcap_scope"} <= set(claim_ids(SELF_FUNDED))
    assert "ihcap_timing" not in claim_ids(SELF_FUNDED)
    assert "Labor" in result.regulator.name


def test_nj_regulated_gets_ihcap_path_and_flags_the_missing_deadline():
    result = triage(NJ)
    assert {"ihcap_internal_first", "ihcap_timing", "nj_dobi_hotline"} <= set(claim_ids(NJ))
    assert "DOBI" in result.regulator.name
    assert any("doesn’t state a deadline" in u for u in result.uncertainties)


def test_marketplace_flags_the_unconfirmed_cms_rule():
    result = triage({"coverage_source": "self_bought", "purchase_channel": "get_covered_nj"})
    assert any("CMS-0057-F" in u for u in result.uncertainties)


def test_medicaid_marks_the_conflicting_fair_hearing_claim_for_review():
    result = triage({"coverage_source": "medicaid"})
    flagged = {c.id for c in result.claims if c.needs_review}
    assert flagged == {"medicaid_fair_hearing"}
    assert any("July 1, 2026" in u for u in result.uncertainties)


def test_medicare_advantage_vs_original():
    assert "ma_reconsideration_60" in claim_ids({"coverage_source": "medicare", "medicare_kind": "advantage"})
    original = triage({"coverage_source": "medicare", "medicare_kind": "original"})
    assert "ma_reconsideration_60" not in [c.id for c in original.claims]
    assert any("Original Medicare" in u for u in original.uncertainties)


def test_unknown_gets_no_plan_specific_deadlines_only_how_to_find_out():
    result = triage({"coverage_source": "unsure"})
    ids = set(claim_ids({"coverage_source": "unsure"}))
    assert not ids & {"internal_appeal_window", "ihcap_timing", "medicaid_appeal_60", "ma_reconsideration_60"}
    assert result.regulator is None
    assert any("HR" in step for step in result.how_to_confirm)


def test_grandfathered_and_not_sure_answers_add_caveats():
    result = triage({**SELF_FUNDED, "grandfathered": "unsure", "employer_type": "unsure"})
    assert result.confidence == "needs-confirmation"
    assert any("grandfathered" in u for u in result.uncertainties)
    assert result.uncertainties[0].startswith("Some of your answers were “not sure,”")


# ---------------------------------------------------------------- suggestions from letter clues


@pytest.mark.parametrize(
    "signals,expected",
    [
        (["medicaid"], {"coverage_source": "medicaid"}),
        (["medicare", "new-jersey"], {"coverage_source": "medicare"}),
        (["self-funded", "erisa"], {"coverage_source": "job", "employer_type": "private", "funding": "self_funded"}),
        (["erisa"], {"coverage_source": "job", "employer_type": "private"}),
        (["fully-insured", "new-jersey"], {"funding": "fully_insured", "issued_state": "nj"}),
        (["marketplace"], {"coverage_source": "self_bought", "purchase_channel": "get_covered_nj"}),
        ([], {}),
        (["urgent", "unknown-code"], {}),
    ],
)
def test_suggestions(signals, expected):
    result = suggest(signals)
    assert result.answers == expected
    assert bool(result.reasons) == bool(expected)


def test_suggested_answers_are_always_valid_options():
    for codes in (["medicaid"], ["self-funded", "erisa"], ["fully-insured", "new-jersey"], ["marketplace"]):
        for qid, value in suggest(codes).answers.items():
            assert value in {o.value for o in QUESTIONS[qid].options}


# ---------------------------------------------------------------- API


def test_flow_endpoint(client):
    body = client.get("/api/triage/flow").json()
    assert body["start"] == "coverage_source"
    assert set(body["questions"]) == set(QUESTIONS)


def test_triage_endpoint(client):
    res = client.post("/api/triage", json={"answers": SELF_FUNDED})
    assert res.status_code == 200
    body = res.json()
    assert body["plan_type"] == "self-funded"
    src = body["claims"][0]["sources"][0]
    assert src["url"].startswith("https://") and src["verification"] in {"verified", "needs-review"}


def test_triage_endpoint_rejects_bad_answers_with_a_reason(client):
    res = client.post("/api/triage", json={"answers": {"coverage_source": "<b>job</b>"}})
    assert res.status_code == 422
    assert "isn’t a valid answer" in res.json()["message"]
    assert "<b>" not in res.text


def test_triage_endpoint_rejects_oversized_payloads(client):
    res = client.post("/api/triage", json={"answers": {f"q{i}": "x" for i in range(11)}})
    assert res.status_code in (413, 422)


def test_suggest_endpoint(client):
    res = client.post("/api/triage/suggest", json={"signals": ["self-funded"]})
    assert res.json()["answers"]["funding"] == "self_funded"
