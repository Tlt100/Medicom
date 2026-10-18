"""Classifies a plan from triage answers and builds a cited profile of what that means.

The classifier only uses the user's own answers. Letter clues can *suggest* answers (suggest()), but the
user confirms every one, so a plan type is never inferred silently from document text.
"""

from typing import Dict, List, Optional, Tuple

from patientshield.core.claims import CLAIMS
from patientshield.core.sources.service import get_source
from patientshield.core.triage.flow import QUESTIONS, START, walk
from patientshield.core.triage.models import (
    AnswerOut,
    ClaimOut,
    FlowOut,
    OptionOut,
    PlanType,
    QuestionOut,
    Regulator,
    SourceRef,
    Suggestion,
    TriageResult,
)

HOW_TO_CONFIRM = [
    "Look at your insurance card. Medicare, Medicare Advantage, and NJ FamilyCare cards say so.",
    "Check your plan documents (the Summary Plan Description or Summary of Benefits and Coverage) for the words “self-funded,” "
    "“self-insured,” “fully insured,” “ERISA,” or “grandfathered,” and for the state where the policy was issued.",
    "If you get coverage through work, ask HR: “Is our health plan self-funded or fully insured, and which state issued the policy?”",
    "Call the member services number on your card and ask who regulates your plan.",
]

LABELS: Dict[str, str] = {
    "nj-regulated": "New Jersey-regulated plan",
    "marketplace": "Get Covered New Jersey marketplace plan",
    "self-funded": "Self-funded employer plan (ERISA)",
    "medicaid": "NJ FamilyCare / Medicaid",
    "medicare": "Medicare",
    "other-state": "Plan issued in another state",
    "government-or-religious": "Government or religious-organization plan",
    "unknown": "Plan type not yet known",
}


# ---------------------------------------------------------------- flow & suggestions


def flow() -> FlowOut:
    return FlowOut(
        start=START,
        questions={
            q.id: QuestionOut(
                id=q.id,
                prompt=q.prompt,
                help=q.help,
                options=[OptionOut(value=o.value, label=o.label, hint=o.hint, next=o.next) for o in q.options],
            )
            for q in QUESTIONS.values()
        },
    )


def suggest(signals: List[str]) -> Suggestion:
    """Maps letter clues to suggested answers. Suggestions are pre-selected in the UI but never auto-submitted."""
    s = set(signals)
    if "medicaid" in s:
        return Suggestion(answers={"coverage_source": "medicaid"}, reasons=["Your letter mentions Medicaid or NJ FamilyCare."])
    if "medicare" in s:
        return Suggestion(answers={"coverage_source": "medicare"}, reasons=["Your letter mentions Medicare."])
    if "self-funded" in s or ("erisa" in s and "fully-insured" not in s):
        reasons = []
        if "self-funded" in s:
            reasons.append("Your letter mentions a self-funded or self-insured plan.")
        if "erisa" in s:
            reasons.append("Your letter mentions ERISA, which usually means a job-based plan.")
        answers = {"coverage_source": "job", "employer_type": "private"}
        if "self-funded" in s:
            answers["funding"] = "self_funded"
        return Suggestion(answers=answers, reasons=reasons)
    if "marketplace" in s:
        return Suggestion(
            answers={"coverage_source": "self_bought", "purchase_channel": "get_covered_nj"},
            reasons=["Your letter mentions Get Covered New Jersey or the Marketplace."],
        )
    if "fully-insured" in s:
        answers = {"funding": "fully_insured"}
        reasons = ["Your letter mentions a fully insured plan."]
        if "new-jersey" in s:
            answers["issued_state"] = "nj"
            reasons.append("Your letter mentions New Jersey.")
        return Suggestion(answers=answers, reasons=reasons)
    return Suggestion(answers={}, reasons=[])


# ---------------------------------------------------------------- classification


def classify(answers: Dict[str, str]) -> Tuple[PlanType, bool]:
    """Returns (plan type, needs_confirmation). Assumes answers already passed walk()."""
    source = answers["coverage_source"]
    if source == "medicaid":
        return "medicaid", False
    if source == "medicare":
        return "medicare", answers.get("medicare_kind") == "unsure"
    if source == "unsure":
        return "unknown", True
    if source == "self_bought":
        channel = answers["purchase_channel"]
        if channel == "get_covered_nj":
            return "marketplace", False
        if channel == "other_state":
            return "other-state", False
        return "nj-regulated", channel == "unsure"
    # job-based
    employer = answers["employer_type"]
    if employer in {"government", "religious"}:
        return "government-or-religious", False
    funding = answers["funding"]
    if funding == "unsure":
        return "unknown", True
    if funding == "self_funded":
        return "self-funded", employer == "unsure"
    state = answers["issued_state"]
    if state == "other":
        return "other-state", False
    return "nj-regulated", employer == "unsure" or state == "unsure"


# ---------------------------------------------------------------- profiles


def source_ref(source_id: str) -> SourceRef:
    s = get_source(source_id)
    if s is None:
        raise KeyError(f"unknown source id {source_id}")
    return SourceRef(
        id=s.id,
        title=s.title,
        citation=s.citation,
        authority=s.authority,
        url=str(s.url),
        source_type=s.source_type.value,
        verification=s.verification.value,
    )


def claim_out(claim_id: str) -> ClaimOut:
    claim = CLAIMS[claim_id]
    sources = [source_ref(sid) for sid in claim.source_ids]
    return ClaimOut(id=claim.id, text=claim.text, sources=sources, needs_review=any(s.verification == "needs-review" for s in sources))


def _profile(plan: PlanType, answers: Dict[str, str]) -> Tuple[str, Optional[Regulator], List[str], List[str]]:
    """Returns (summary, regulator, claim ids, uncertainties) for a plan type."""
    dobi = Regulator(name="New Jersey Department of Banking and Insurance (DOBI)", source=source_ref("nj-dobi-consumer"))
    grandfathered = answers.get("grandfathered")
    uncertainties: List[str] = []
    if grandfathered in {"yes", "unsure"}:
        uncertainties.append(
            "If your plan is grandfathered, some federal appeal and external review rules may not apply. Check your plan documents."
        )

    if plan in {"nj-regulated", "marketplace"}:
        summary = (
            "Your plan appears to be regulated by New Jersey. After the plan’s internal appeal, New Jersey’s Independent Health Care "
            "Appeals Program (IHCAP) can send your case to an independent reviewer."
        )
        if plan == "marketplace":
            summary = (
                "Your plan was bought through Get Covered New Jersey, the state-run marketplace. IHCAP’s exclusions (self-funded plans, "
                "Medicare, Medicare Advantage, and out-of-state contracts) don’t include marketplace plans, so after the plan’s internal "
                "appeal you can generally ask IHCAP for an independent review."
            )
            uncertainties.append(
                "Whether CMS’s prior authorization rule (CMS-0057-F) reaches Get Covered New Jersey plans is unconfirmed: the rule names "
                "plans on the federal marketplace, and New Jersey runs its own."
            )
        uncertainties.append(
            "NJ DOBI’s IHCAP page doesn’t state a deadline for requesting external review. Use the deadline in the plan’s final "
            "internal appeal decision, and confirm it with NJ DOBI."
        )
        claims = [
            "internal_appeal_window",
            "internal_decision_timing",
            "ihcap_internal_first",
            "ihcap_timing",
            "external_review_binding",
            "ihcap_scope",
            "nj_dobi_hotline",
        ]
        return summary, dobi, claims, uncertainties

    if plan == "self-funded":
        summary = (
            "Self-funded employer plans are governed mainly by federal law (ERISA), not New Jersey insurance law, so New Jersey’s IHCAP "
            "program isn’t available. You appeal to the plan first; external review, if your plan offers it, also goes through the plan."
        )
        regulator = Regulator(
            name="U.S. Department of Labor, Employee Benefits Security Administration (EBSA)", source=source_ref("dol-filing-a-claim")
        )
        claims = ["erisa_scope", "erisa_appeal_window", "urgent_72h", "erisa_external", "external_review_4_months", "ihcap_scope"]
        return summary, regulator, claims, uncertainties

    if plan == "medicaid":
        summary = (
            "NJ FamilyCare (Medicaid) has its own appeal system: first an appeal to your managed care plan, then a State fair hearing. "
            "Deadlines are short, so act on the dates in your notice."
        )
        regulator = Regulator(
            name="NJ Department of Human Services, Division of Medical Assistance and Health Services (DMAHS)",
            source=source_ref("nj-dmahs-mc-26-06"),
        )
        uncertainties.append(
            "New Jersey changed parts of its Medicaid fair hearing process on July 1, 2026, and official sources give different "
            "deadlines. PatientShield has flagged this for review. Use the deadline printed on your notice and act quickly."
        )
        return summary, regulator, ["medicaid_appeal_60", "medicaid_fair_hearing", "prior_auth_reason"], uncertainties

    if plan == "medicare":
        kind = answers.get("medicare_kind")
        regulator = Regulator(name="Medicare (Centers for Medicare & Medicaid Services)", source=source_ref("medicare-gov-appeals"))
        claims = ["medicare_written", "ihcap_scope"]
        if kind == "advantage":
            summary = "Medicare Advantage plans follow Medicare’s appeal system, which starts with asking the plan to reconsider."
            claims[1:1] = ["ma_reconsideration_60", "prior_auth_reason"]
        else:
            summary = "Medicare has its own appeal system, separate from New Jersey insurance rules. Your notice explains the first step."
            uncertainties.append(
                "PatientShield doesn’t yet cover Original Medicare’s deadlines. Follow the instructions and dates printed on your notice."
                if kind == "original"
                else "Find out whether you have Original Medicare or a Medicare Advantage plan; the first appeal step and deadline differ."
            )
        return summary, regulator, claims, uncertainties

    if plan == "other-state":
        summary = (
            "Because the policy wasn’t issued in New Jersey, New Jersey’s IHCAP program isn’t available. Appeal to the plan first, then "
            "contact the insurance department in the state where the policy was issued about external review."
        )
        return summary, None, ["internal_appeal_window", "ihcap_scope"], uncertainties

    if plan == "government-or-religious":
        summary = (
            "Plans sponsored by government employers, and by most religious organizations, are exceptions to the usual federal claims "
            "rules for private employer plans. PatientShield doesn’t cover these plans yet. Ask the plan administrator which appeal "
            "rules apply."
        )
        return summary, None, ["erisa_scope"], uncertainties

    summary = (
        "Your appeal rights depend on what kind of plan you have, so PatientShield won’t show plan-specific steps yet. "
        "The steps below can tell you your plan type in a few minutes."
    )
    return summary, None, ["ihcap_scope", "erisa_scope"], uncertainties


def triage(answers: Dict[str, str]) -> TriageResult:
    path = walk(answers)
    plan, needs_confirmation = classify(answers)
    summary, regulator, claim_ids, uncertainties = _profile(plan, answers)
    if needs_confirmation and plan != "unknown":
        uncertainties.insert(0, "Some of your answers were “not sure,” so confirm your plan type before relying on these steps.")
    return TriageResult(
        plan_type=plan,
        label=LABELS[plan],
        confidence="needs-confirmation" if needs_confirmation else "confirmed",
        summary=summary,
        regulator=regulator,
        claims=[claim_out(c) for c in claim_ids],
        uncertainties=[u for u in uncertainties if u],
        how_to_confirm=HOW_TO_CONFIRM,
        answers=[AnswerOut(question=q.prompt, answer=o.label) for q, o in path],
    )
