"""Builds a cited action plan from the letter's facts, the confirmed plan type, and the user's situation.

Rules:
- Legal statements only come from CLAIMS (each cites verified sources). Practical advice is labelled "practical".
- Letter facts are always shown as quotes with page numbers, never paraphrased into rules.
- Deadlines say what they're counted from and whether they come from the letter or a general rule.
  When both exist, the user is told to plan around the earlier one; PatientShield never says a plan broke a rule.
- Unknown plan types get no rule-based deadlines, only how to find out.
"""

import datetime as dt
import re
from typing import Dict, List, Optional, Tuple

from ..triage.models import ClaimOut, PlanType
from ..triage.service import _source_ref, claim_out, triage
from .dates import apply_duration, describe, parse_duration
from .models import ActionPlan, Comparison, Contact, Deadline, PlanRequest, StatedDeadline, Step

DISCLAIMER = (
    "PatientShield is an educational tool, not legal advice, and it can’t predict or guarantee the outcome of an appeal. "
    "Deadlines here are general rules and what your letter says; your plan’s documents control. When in doubt, act early and "
    "confirm in writing. For urgent care, contact your plan now and ask for an expedited appeal. For emergencies, call 911."
)

PLAN_STATE_REGULATED = {"nj-regulated", "marketplace"}
PRIVATE_INSURANCE = {"nj-regulated", "marketplace", "self-funded", "other-state"}

# Rule-based first-appeal windows: claim id, duration, and what the window is counted from.
INTERNAL_RULES: Dict[str, Tuple[str, Tuple[int, str, str], str]] = {
    "nj-regulated": ("internal_appeal_window", (180, "days", "calendar"), "received"),
    "marketplace": ("internal_appeal_window", (180, "days", "calendar"), "received"),
    "other-state": ("internal_appeal_window", (180, "days", "calendar"), "received"),
    "self-funded": ("erisa_appeal_window", (180, "days", "calendar"), "received"),
    "medicaid": ("medicaid_appeal_60", (60, "days", "calendar"), "letter"),
}


def _anchor(text: str) -> str:
    """What a letter's time limit counts from: the date on the letter, or when it was received."""
    t = text.lower()
    if re.search(r"\bdate (?:of|on) (?:this|the) (?:letter|notice)\b", t):
        return "letter"
    if "receiv" in t:
        return "received"
    return "unknown"


def _days(duration: Tuple[int, str, str]) -> int:
    qty, unit, _ = duration
    return qty * 30 if unit == "months" else qty * 7 if unit == "weeks" else qty


class _Builder:
    def __init__(self, req: PlanRequest, today: dt.date):
        self.req = req
        self.today = today
        self.result = triage(req.answers)
        self.plan: PlanType = self.result.plan_type
        self.letter = req.letter
        self.sit = req.situation
        self.received = self.sit.date_received or self.letter.letter_date
        self.uncertainties: List[str] = list(self.result.uncertainties)
        self.deadlines: List[Deadline] = []
        self._claims: Dict[str, ClaimOut] = {}

    def claim(self, claim_id: str) -> ClaimOut:
        if claim_id not in self._claims:
            self._claims[claim_id] = claim_out(claim_id)
        return self._claims[claim_id]

    @property
    def job_based(self) -> bool:
        return self.req.answers.get("coverage_source") == "job"

    @property
    def medicare_advantage(self) -> bool:
        return self.plan == "medicare" and self.req.answers.get("medicare_kind") == "advantage"

    @property
    def urgent(self) -> bool:
        return self.sit.urgent == "yes"

    # ------------------------------------------------------------ deadlines

    def _start_for(self, anchor: str) -> Tuple[Optional[dt.date], str]:
        if anchor == "letter" and self.letter.letter_date:
            return self.letter.letter_date, f"the date on the letter ({describe(self.letter.letter_date)})"
        if self.sit.date_received:
            return self.sit.date_received, f"the date you received it ({describe(self.sit.date_received)})"
        if self.letter.letter_date:
            return self.letter.letter_date, f"the date printed on the letter ({describe(self.letter.letter_date)})"
        return None, ""

    def _add(self, id_: str, label: str, start: dt.date, duration, basis: str, kind: str, **extra) -> Deadline:
        due = apply_duration(start, duration)
        note = extra.pop("note", None)
        if duration[2] == "business":
            note = ((note + " ") if note else "") + "Business days skip weekends; we did not account for public holidays."
        days_left = (due - self.today).days
        d = Deadline(id=id_, label=label, date=due, basis=basis, kind=kind, days_left=days_left, passed=days_left < 0, note=note, **extra)
        self.deadlines.append(d)
        return d

    def _letter_deadline(
        self, id_: str, label: str, stated: StatedDeadline, start_override: Optional[dt.date] = None
    ) -> Optional[Deadline]:
        duration = parse_duration(stated.text) or parse_duration(stated.normalized)
        if not duration:
            return None
        if start_override:
            start, from_text = start_override, f"the final appeal decision ({describe(start_override)})"
        else:
            start, from_text = self._start_for(_anchor(stated.text))
        if not start:
            return None
        note = None
        if _anchor(stated.text) == "unknown" and not start_override:
            note = "The letter doesn’t say what this is counted from, so we counted from the earliest date we have."
        return self._add(id_, label, start, duration, f"“{stated.text}”, counted from {from_text}", "letter", quote=stated.quote, note=note)

    def build_deadlines(self) -> None:
        not_yet = self.sit.internal_appeal == "not_yet"
        decided = self.sit.internal_appeal == "decided"
        if not_yet and self.letter.appeal_deadline:
            self._letter_deadline("letter-appeal", "Appeal deadline stated in your letter", self.letter.appeal_deadline)
        if not_yet:
            for i, stated in enumerate(self.letter.other_time_limits):
                self._letter_deadline(f"letter-other-{i}", "Other time limit in your letter", stated)
        if self.plan == "unknown":
            return

        rule = INTERNAL_RULES.get(self.plan)
        if self.medicare_advantage:
            rule = ("ma_reconsideration_60", (60, "days", "calendar"), "received")
        if not_yet and rule:
            claim_id, duration, anchor = rule
            start, from_text = self._start_for(anchor)
            if start:
                self._add(
                    "rule-appeal",
                    "General rule: last day to file the first appeal",
                    start,
                    duration,
                    f"{duration[0]} calendar days from {from_text}",
                    "rule",
                    claim=self.claim(claim_id),
                )
            else:
                self.uncertainties.append("Add the date you received the letter to see calendar deadlines.")

        if decided and self.sit.final_decision_date:
            if self.letter.external_review_deadline:
                self._letter_deadline(
                    "letter-external",
                    "External review deadline stated in your letter",
                    self.letter.external_review_deadline,
                    start_override=self.sit.final_decision_date,
                )
            if self.plan in PLAN_STATE_REGULATED or self.plan == "self-funded":
                note = (
                    "NJ DOBI’s IHCAP page doesn’t state a filing deadline; this is the general federal rule."
                    if self.plan in PLAN_STATE_REGULATED
                    else None
                )
                self._add(
                    "rule-external",
                    "General rule: last day to request external review",
                    self.sit.final_decision_date,
                    (4, "months", "calendar"),
                    f"4 months from the final appeal decision ({describe(self.sit.final_decision_date)})",
                    "rule",
                    claim=self.claim("external_review_4_months"),
                    note=note,
                )
        elif decided:
            self.uncertainties.append("Add the date of the final appeal decision to see the external review deadline.")

        if not self.sit.date_received and self.letter.letter_date and self.deadlines:
            self.uncertainties.append(
                "We counted from the date printed on the letter because you didn’t enter when you received it. If it arrived later, "
                "some deadlines may be later. If you’re unsure, plan around the earlier date."
            )

    def plan_around(self) -> Optional[str]:
        upcoming = sorted((d for d in self.deadlines if not d.passed), key=lambda d: d.date)
        passed = [d for d in self.deadlines if d.passed]
        if upcoming:
            first = upcoming[0]
            text = f"Plan around {describe(first.date)} ({first.days_left} days from today): {first.label.lower()}."
            if len(upcoming) > 1:
                text += " It’s the earliest date below."
            return text
        if passed:
            return (
                "The dates we calculated have passed. Contact the plan right away and ask in writing whether you can still appeal, "
                "and whether an exception applies. Only the plan or a regulator can say."
            )
        return None

    # ------------------------------------------------------------ comparisons

    def internal_claim_ids(self) -> List[str]:
        if self.medicare_advantage:
            return ["ma_reconsideration_60"]
        rule = INTERNAL_RULES.get(self.plan)
        return [rule[0]] if rule else []

    def next_stage_claim_ids(self) -> List[str]:
        return {
            "nj-regulated": ["ihcap_internal_first", "ihcap_timing", "external_review_binding"],
            "marketplace": ["ihcap_internal_first", "ihcap_timing", "external_review_binding"],
            "self-funded": ["erisa_external", "external_review_4_months", "ihcap_scope"],
            "medicaid": ["medicaid_fair_hearing"],
            "medicare": ["medicare_written"],
            "other-state": ["ihcap_scope"],
            "government-or-religious": ["erisa_scope"],
            "unknown": ["ihcap_scope"],
        }[self.plan]

    def comparisons(self) -> List[Comparison]:
        L = self.letter
        rows: List[Comparison] = []
        unknown_note = "Confirm your plan type to see which rule applies." if self.plan == "unknown" else None

        reason_rules = ["prior_auth_reason"] if self.plan == "medicaid" or self.medicare_advantage else []
        rows.append(
            Comparison(
                topic="Why it was denied",
                letter=L.denial_reason or L.denial_statement,
                letter_status="found" if L.denial_reason else "not_found",
                letter_summary="The letter states a reason." if L.denial_reason else "The letter doesn’t explain why.",
                rules=[self.claim(c) for c in reason_rules],
                rules_summary=None
                if reason_rules
                else "Our source library doesn’t yet include a rule for your plan type on how reasons must be explained. You can still "
                "ask the plan in writing for the specific reason and the criteria it used.",
            )
        )

        stated = L.appeal_deadline
        internal = self.internal_claim_ids()
        note = None
        stated_duration = parse_duration(stated.text) if stated else None
        rule = INTERNAL_RULES.get(self.plan) or (
            ("ma_reconsideration_60", (60, "days", "calendar"), "received") if self.medicare_advantage else None
        )
        if stated_duration and rule:
            if _days(stated_duration) < _days(rule[1]):
                note = (
                    "Your letter gives less time than the general rule we cite. Plan around the letter’s earlier date, and ask the plan "
                    "in writing which deadline applies."
                )
            else:
                note = "Your letter’s deadline is at least as long as the general rule we cite."
        elif not stated:
            note = "Your letter doesn’t state a deadline. Ask the plan in writing, and don’t wait to act."
        rows.append(
            Comparison(
                topic="Deadline for the first appeal",
                letter=stated.quote if stated else None,
                letter_status="found" if stated else "not_found",
                letter_summary=f"Within {stated.text}" if stated else "No deadline found in the letter.",
                rules=[self.claim(c) for c in internal],
                rules_summary=unknown_note
                or (None if internal else "PatientShield doesn’t cover this deadline for your plan type yet. Follow your notice."),
                note=note,
            )
        )

        how = L.appeal_instructions[0] if L.appeal_instructions else None
        rows.append(
            Comparison(
                topic="How to appeal",
                letter=how,
                letter_status="found" if how else "not_found",
                letter_summary="The letter explains where or how to appeal." if how else "No appeal instructions found in the letter.",
                rules=[self.claim("medicare_written")] if self.plan == "medicare" else [],
                rules_summary=None
                if self.plan == "medicare"
                else "Your letter is the main source for where and how to send your appeal. If it doesn’t say, ask the plan in writing.",
            )
        )

        ext = L.external_review_deadline
        rows.append(
            Comparison(
                topic="If the first appeal is denied",
                letter=ext.quote if ext else None,
                letter_status="found" if ext else "not_found",
                letter_summary=f"Within {ext.text}" if ext else "The letter doesn’t describe the next step.",
                rules=[self.claim(c) for c in self.next_stage_claim_ids()],
                rules_summary=unknown_note,
            )
        )

        if self.urgent or L.urgent_mentioned:
            rows.append(
                Comparison(
                    topic="Urgent care",
                    letter=None,
                    letter_status="found" if L.urgent_mentioned else "not_found",
                    letter_summary="Your letter mentions expedited or urgent appeals."
                    if L.urgent_mentioned
                    else "The letter doesn’t mention urgent appeals.",
                    rules=[self.claim("urgent_72h")] if self.job_based else [],
                    rules_summary=None if self.job_based else "Ask the plan for an expedited appeal and follow the timeline it gives you.",
                )
            )
        return rows

    # ------------------------------------------------------------ steps

    def steps(self) -> List[Step]:
        L, S = self.letter, self.sit
        out: List[Step] = []
        earliest = min((d.date for d in self.deadlines if not d.passed), default=None)

        if self.urgent:
            out.append(
                Step(
                    id="urgent",
                    title="Ask for an expedited (urgent) appeal now",
                    detail="Call the number on your letter and say: “I am requesting an expedited appeal because waiting could seriously "
                    "harm my health.” Ask your doctor to call or write to support it. For a medical emergency, call 911 first.",
                    kind="urgent",
                    claims=[self.claim("urgent_72h")] if self.job_based else [],
                )
            )
        if self.plan == "unknown":
            out.append(
                Step(
                    id="confirm-plan",
                    title="Confirm your plan type first",
                    detail="Appeal rights depend on it. " + " ".join(self.result.how_to_confirm),
                    kind="practical",
                )
            )
        if self.deadlines:
            out.append(
                Step(
                    id="calendar",
                    title="Put your deadlines on a calendar",
                    detail="Mark every date in the deadlines list. If dates differ, plan around the earliest.",
                    kind="letter" if any(d.kind == "letter" for d in self.deadlines) else "rule",
                    due=earliest,
                )
            )
        if L.denial_reason is None:
            out.append(
                Step(
                    id="ask-reason",
                    title="Ask the plan for the specific reason, in writing",
                    detail="Your letter doesn’t explain why. Ask which plan rule or clinical criteria the decision was based on.",
                    kind="practical",
                    quote=L.denial_statement,
                )
            )
        else:
            out.append(
                Step(
                    id="ask-documents",
                    title="Ask for copies of what the plan relied on",
                    detail=(
                        "Ask in writing for the documents, records and criteria used in the decision, so you can answer the stated reason."
                    ),
                    kind="practical",
                    quote=L.denial_reason,
                )
            )
        out.append(
            Step(
                id="doctor",
                title="Ask your doctor for a supporting letter",
                detail="A letter explaining why you need the care, responding to the plan’s stated reason, often carries weight.",
                kind="practical",
            )
        )

        how = L.appeal_instructions[0] if L.appeal_instructions else None
        appeal_due = min((d.date for d in self.deadlines if d.id in {"letter-appeal", "rule-appeal"}), default=None)
        if S.internal_appeal == "not_yet":
            if self.plan in PRIVATE_INSURANCE:
                out.append(
                    Step(
                        id="file-appeal",
                        title="File a written internal appeal",
                        detail="Send it the way your letter says. Keep a copy and proof of when you sent it.",
                        kind="rule",
                        due=appeal_due,
                        claims=[self.claim(c) for c in self.internal_claim_ids()],
                        quote=how,
                    )
                )
            elif self.plan == "medicaid":
                out.append(
                    Step(
                        id="file-appeal",
                        title="Ask your plan for an appeal",
                        detail="Call or write to the plan as your notice describes. If you want services to continue during the appeal, "
                        "check your notice for a shorter time limit to ask.",
                        kind="rule",
                        due=appeal_due,
                        claims=[self.claim("medicaid_appeal_60")],
                        quote=how,
                    )
                )
            elif self.medicare_advantage:
                out.append(
                    Step(
                        id="file-appeal",
                        title="Ask the plan to reconsider",
                        detail="Follow the instructions in your plan’s written decision.",
                        kind="rule",
                        due=appeal_due,
                        claims=[self.claim("ma_reconsideration_60")],
                        quote=how,
                    )
                )
            elif self.plan == "medicare":
                out.append(
                    Step(
                        id="file-appeal",
                        title="Follow the appeal instructions on your notice",
                        detail="Medicare’s first appeal step and deadline depend on your type of Medicare. Your notice explains them.",
                        kind="rule",
                        claims=[self.claim("medicare_written")],
                        quote=how,
                    )
                )
            elif self.plan == "government-or-religious":
                out.append(
                    Step(
                        id="ask-rules",
                        title="Ask the plan administrator which appeal rules apply",
                        detail="Then follow the appeal instructions in your letter.",
                        kind="rule",
                        claims=[self.claim("erisa_scope")],
                        quote=how,
                    )
                )
        elif S.internal_appeal == "waiting" and self.plan in PRIVATE_INSURANCE:
            out.append(
                Step(
                    id="watch-decision",
                    title="Watch for the decision on your appeal",
                    detail="If it’s late, follow up in writing.",
                    kind="rule",
                    claims=[self.claim("internal_decision_timing")],
                )
            )

        next_title = {
            "nj-regulated": "Request independent external review through NJ IHCAP",
            "marketplace": "Request independent external review through NJ IHCAP",
            "self-funded": "Request external review through your plan",
            "medicaid": "Request a State fair hearing",
            "medicare": "Go to the next level of appeal",
            "other-state": "Ask the insurance department in the state that issued your policy about external review",
        }.get(self.plan)
        if next_title:
            ext_due = min((d.date for d in self.deadlines if d.id in {"letter-external", "rule-external"}), default=None)
            prefix = "" if S.internal_appeal == "decided" else "If the appeal is denied: "
            out.append(
                Step(
                    id="next-stage",
                    title=prefix + next_title[0].lower() + next_title[1:] if prefix else next_title,
                    detail="Include the denial letters, your plan documents, your doctor’s letter and relevant medical records.",
                    kind="rule",
                    due=ext_due,
                    claims=[self.claim(c) for c in self.next_stage_claim_ids()],
                    quote=self.letter.external_review_deadline.quote if self.letter.external_review_deadline else None,
                )
            )
        out.append(
            Step(
                id="records",
                title="Keep a record of every call and letter",
                detail="Write down the date, the person you spoke with, and any reference number. Send important things in writing.",
                kind="practical",
            )
        )
        return out

    # ------------------------------------------------------------ lists

    def documents(self) -> List[str]:
        docs = [
            "The denial letter (all pages)",
            "Your insurance card",
            "Your plan documents (Summary of Benefits and Coverage, member handbook, or Summary Plan Description)",
            "A letter from your doctor explaining why you need the care",
            "Relevant medical records and test results",
            "A log of calls and letters: dates, names, reference numbers",
        ]
        if self.sit.care_received == "yes":
            docs.insert(2, "Bills and any Explanation of Benefits (EOB) for the care")
        if self.plan == "medicaid":
            docs[1] = "Your NJ FamilyCare ID card"
        return docs

    def questions(self) -> List[str]:
        q: List[str] = []
        if self.letter.denial_reason is None:
            q.append("What is the specific reason for this decision, and which plan rule or criteria did you use?")
        if self.letter.appeal_deadline is None:
            q.append("What is the exact deadline to appeal, and what date is it counted from?")
        if not self.letter.appeal_instructions:
            q.append("Where and how do I send an appeal (address, fax, or online)?")
        if self.plan in {"unknown", "other-state"} or self.result.confidence == "needs-confirmation":
            q.append("Is my plan self-funded or fully insured, and which state issued the policy?")
        if self.urgent or self.letter.urgent_mentioned:
            q.append("Can this be handled as an expedited (urgent) appeal?")
        if self.plan == "medicaid":
            q.append("If I appeal, will my services continue while you decide, and by when must I ask?")
        q += [
            "Can you send me copies of the documents and criteria used to make this decision?",
            "Can my doctor speak with your medical reviewer?",
        ]
        return q

    def contacts(self) -> List[Contact]:
        c: List[Contact] = []
        if self.plan in PLAN_STATE_REGULATED or self.plan == "unknown":
            c.append(
                Contact(
                    name="NJ DOBI Independent Health Care Appeals Program",
                    when="After a final internal appeal denial, for New Jersey-regulated plans",
                    phone="1-888-393-1062",
                    source=_source_ref("nj-dobi-ihcap"),
                    claim=self.claim("ihcap_contact"),
                )
            )
            c.append(
                Contact(
                    name="NJ DOBI Consumer Hotline",
                    when="Problems with how a New Jersey-regulated insurer handles your claim",
                    phone="1-800-446-7467",
                    source=_source_ref("nj-dobi-consumer"),
                    claim=self.claim("nj_dobi_hotline"),
                )
            )
        if self.plan in {"self-funded", "unknown"}:
            c.append(
                Contact(
                    name="U.S. Department of Labor, Employee Benefits Security Administration",
                    when="Questions about a private employer plan, including self-funded plans",
                    source=_source_ref("dol-filing-a-claim"),
                )
            )
        if self.plan == "medicaid":
            c.append(
                Contact(
                    name="NJ Division of Medical Assistance and Health Services",
                    when="NJ FamilyCare fair hearings (check your notice for current instructions)",
                    source=_source_ref("nj-dmahs-mc-26-06"),
                )
            )
        if self.plan == "medicare":
            c.append(
                Contact(
                    name="Medicare appeals", when="How Medicare appeals work, level by level", source=_source_ref("medicare-gov-appeals")
                )
            )
        return c

    def build(self) -> ActionPlan:
        self.build_deadlines()
        comparisons = self.comparisons()
        steps = self.steps()
        return ActionPlan(
            plan_type=self.plan,
            label=self.result.label,
            today=self.today,
            comparisons=comparisons,
            deadlines=sorted(self.deadlines, key=lambda d: d.date),
            plan_around=self.plan_around(),
            steps=steps,
            documents=self.documents(),
            questions=self.questions(),
            contacts=self.contacts(),
            uncertainties=list(dict.fromkeys(u for u in self.uncertainties if u)),
            disclaimer=DISCLAIMER,
        )


def build_plan(req: PlanRequest, today: Optional[dt.date] = None) -> ActionPlan:
    return _Builder(req, today or dt.date.today()).build()
