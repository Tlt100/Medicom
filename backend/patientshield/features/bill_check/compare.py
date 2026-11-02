"""Lines up a bill with an EOB and points out differences worth asking about.

Language rule: a flag describes a difference and a question to ask. It never says a bill is wrong, an error,
an overcharge, or illegal; bills and EOBs differ for ordinary reasons (a second EOB, a payment already made).
Each flag either cites statements from the verified source library or is marked as a practical suggestion.
"""

import re
from typing import Dict, List, Optional, Sequence, Set, Tuple

from patientshield.core.triage.service import claim_out
from patientshield.features.bill_check.models import Comparison, DocumentIn, Flag, LineItemIn, Match

DISCLAIMER = (
    "These are differences worth asking about, not findings that anything is wrong. A bill and an EOB can differ for "
    "ordinary reasons, such as a payment you already made or a service on a separate EOB. Medicom doesn't decide "
    "whether a bill is correct; your provider and your plan can explain each line."
)

NEXT_STEPS = ["compare_before_paying", "ask_itemized_bill", "billing_questions_contact_provider", "eob_not_a_bill"]

_WORD = re.compile(r"[a-z]{3,}")


def money(c: int) -> str:
    return f"-${abs(c) / 100:,.2f}" if c < 0 else f"${c / 100:,.2f}"


def _words(text: str) -> Set[str]:
    return set(_WORD.findall(text.lower()))


def _similar(a: str, b: str) -> bool:
    wa, wb = _words(a), _words(b)
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.5


def _match_reasons(b: LineItemIn, e: LineItemIn) -> Optional[List[str]]:
    """Why a bill line and an EOB line look like the same service, or None if they don't."""
    if b.service_date and e.service_date and b.service_date != e.service_date:
        return None
    reasons: List[str] = []
    if b.service_date and b.service_date == e.service_date:
        reasons.append("date")
    if b.code and b.code == e.code:
        reasons.append("code")
    elif b.code and e.code:
        return None  # two different billing codes are two different services
    if "billed" in b.amounts and b.amounts.get("billed") == e.amounts.get("billed"):
        reasons.append("charge")
    if _similar(b.description, e.description):
        reasons.append("description")
    if not set(reasons) & {"code", "charge", "description"}:
        return None
    return reasons


_WEIGHT = {"code": 4, "charge": 2, "description": 1, "date": 1}


def match_lines(bill: Sequence[LineItemIn], eob: Sequence[LineItemIn]) -> List[Match]:
    """One-to-one matching, strongest evidence first (code, then charge, then description)."""
    candidates: List[Tuple[int, int, int, List[str]]] = []
    for bi, b in enumerate(bill):
        for ei, e in enumerate(eob):
            reasons = _match_reasons(b, e)
            if reasons:
                candidates.append((-sum(_WEIGHT[r] for r in reasons), bi, ei, reasons))
    candidates.sort()
    used_b: Set[int] = set()
    used_e: Set[int] = set()
    matches: List[Match] = []
    for _, bi, ei, reasons in candidates:
        if bi in used_b or ei in used_e:
            continue
        used_b.add(bi)
        used_e.add(ei)
        matches.append(Match(bill_item_id=bill[bi].id, eob_item_id=eob[ei].id, matched_on=reasons))  # type: ignore[arg-type]
    order = {item.id: n for n, item in enumerate(bill)}
    return sorted(matches, key=lambda m: order[m.bill_item_id])


def _total(doc: DocumentIn, key: str) -> Optional[int]:
    for t in doc.totals:
        if t.key == key:
            return t.amount_cents
    return None


def eob_patient_owes(eob: DocumentIn) -> Optional[int]:
    stated = _total(eob, "patient_owes")
    if stated is not None:
        return stated
    if eob.line_items and all("patient_owes" in i.amounts for i in eob.line_items):
        return sum(i.amounts["patient_owes"] for i in eob.line_items)
    return None


def bill_amount_due(bill: DocumentIn) -> Optional[int]:
    return _total(bill, "amount_due")


def _same_service(a: LineItemIn, b: LineItemIn) -> bool:
    return (a.service_date, a.code, a.amounts.get("billed"), a.description.lower()) == (
        b.service_date,
        b.code,
        b.amounts.get("billed"),
        b.description.lower(),
    )


def compare(eob: DocumentIn, bill: DocumentIn) -> Comparison:
    matches = match_lines(bill.line_items, eob.line_items)
    by_bill = {m.bill_item_id: m for m in matches}
    matched_eob = {m.eob_item_id for m in matches}
    eob_by_id: Dict[str, LineItemIn] = {i.id: i for i in eob.line_items}
    flags: List[Flag] = []

    def add(kind, level, title, detail, bill_ids=(), eob_ids=(), claims=(), practical=False) -> None:
        flags.append(
            Flag(
                id=f"{kind}-{len(flags) + 1}",
                kind=kind,
                level=level,
                title=title,
                detail=detail,
                bill_item_ids=list(bill_ids),
                eob_item_ids=list(eob_ids),
                claims=[claim_out(c) for c in claims],
                practical=practical,
            )
        )

    if not bill.line_items:
        add(
            "no_line_items",
            "ask",
            "This bill doesn’t list individual services",
            "Without a line for each service, the bill can’t be compared with your EOB line by line. You can ask the "
            "provider for a bill that lists each service and its cost.",
            claims=["ask_itemized_bill"],
        )

    # Bill lines with no EOB match: a repeat of another bill line, or simply not on this EOB.
    unmatched_not_on_eob: List[str] = []
    for n, b in enumerate(bill.line_items):
        m = by_bill.get(b.id)
        if m is not None:
            e = eob_by_id[m.eob_item_id]
            billed_b, billed_e = b.amounts.get("billed"), e.amounts.get("billed")
            if billed_b is not None and billed_e is not None and billed_b != billed_e:
                add(
                    "charge_differs",
                    "ask",
                    "The charge for this service is different on the bill and the EOB",
                    f"The bill shows {money(billed_b)}. The EOB shows a provider charge of {money(billed_e)}.",
                    bill_ids=[b.id],
                    eob_ids=[e.id],
                    claims=["compare_before_paying", "billing_questions_contact_provider"],
                )
            continue
        twin = next((o for o in bill.line_items[:n] if _same_service(o, b)), None)
        if twin is not None:
            add(
                "possible_duplicate",
                "ask",
                "This line repeats another line on the bill",
                "It has the same date, description, code and charge as an earlier line, and the EOB lists the service "
                "fewer times. It may be correct (for example, two units of the same service), but it’s worth asking.",
                bill_ids=[twin.id, b.id],
                claims=["billed_twice"],
            )
        else:
            unmatched_not_on_eob.append(b.id)
            add(
                "not_on_eob",
                "ask",
                "This charge isn’t on the EOB you added",
                "We couldn’t find a matching service on this EOB. It may be on a different EOB (plans often send one "
                "per provider or per visit), or the provider may not have sent it to your plan.",
                bill_ids=[b.id],
                claims=["missing_eob_ask_plan"],
            )

    for e in eob.line_items:
        if e.status == "denied":
            add(
                "denied_on_eob",
                "info",
                "Your plan didn’t pay for this service",
                "The EOB marks this line as denied or not covered. If you disagree with that decision, you may be able "
                "to appeal. The Denial Navigator can walk you through a denial notice.",
                eob_ids=[e.id],
                practical=True,
            )
        if e.id not in matched_eob:
            add(
                "on_eob_not_on_bill",
                "info",
                "On the EOB, but not on this bill",
                "This service may be billed separately, for example by a different provider, or not billed yet.",
                eob_ids=[e.id],
                practical=True,
            )

    owes, due = eob_patient_owes(eob), bill_amount_due(bill)
    if owes is not None and due is not None:
        if due > owes:
            extra = " Part of the difference may be the charges that aren’t on this EOB." if unmatched_not_on_eob else ""
            add(
                "amount_due_exceeds_eob",
                "ask",
                "The bill asks for more than the EOB says you owe",
                f"The bill says you owe {money(due)}. The EOB says you owe {money(owes)}, a difference of {money(due - owes)}.{extra}",
                bill_ids=unmatched_not_on_eob,
                claims=["bill_not_above_eob", "in_network_no_balance_bill"],
            )
            add(
                "surprise_bill_context",
                "info",
                "If this was emergency care, or care at an in-network hospital or surgery center",
                "Federal and New Jersey surprise-billing protections may limit what you can be asked to pay. Whether they "
                "apply depends on your plan and where you got care.",
                claims=["nsa_emergency", "nj_out_of_network", "nsa_help_desk"],
            )
        elif due < owes:
            add(
                "amount_due_below_eob",
                "info",
                "The bill asks for less than the EOB says you owe",
                f"The bill says you owe {money(due)}; the EOB says {money(owes)}. Often this means a payment you already "
                "made, such as a copay at the visit, was subtracted.",
                claims=["eob_may_not_show_payments"],
            )

    order = {"ask": 0, "info": 1}
    flags.sort(key=lambda f: order[f.level])
    return Comparison(
        matches=matches,
        flags=flags,
        eob_patient_owes_cents=owes,
        bill_amount_due_cents=due,
        next_steps=[claim_out(c) for c in NEXT_STEPS],
        disclaimer=DISCLAIMER,
    )
