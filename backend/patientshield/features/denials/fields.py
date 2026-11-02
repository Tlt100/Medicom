"""Rule-based extraction of denial-letter details.

Principles:
- Quote, never compose. Every value comes from the document and every field carries citations whose
  `quote` is the exact page text at [start:end].
- Missing means missing. If a detail isn't in the letter, the field says "not_found" with guidance;
  nothing is inferred or filled in.
- Document text is data. It is matched against fixed patterns only and is never interpreted as
  instructions. Text that looks like instructions to software is surfaced as a warning.
"""

import datetime as dt
import re
from typing import Dict, Iterable, List, Optional, Tuple

from patientshield.core.documents.segment import Passage
from patientshield.features.denials.models import Citation, ExtractedField, FieldKey, Signal

LABELS: Dict[str, str] = {
    "denial_reason": "Stated reason for the denial",
    "appeal_instructions": "How to appeal",
    "appeal_deadline": "Appeal deadline stated in the letter",
    "external_review_deadline": "External review or fair hearing deadline",
    "letter_date": "Date of the letter",
    "insurer_name": "Insurer or plan administrator",
    "plan_name": "Plan name",
    "reference_numbers": "Reference numbers",
}

NOT_FOUND_NOTES: Dict[str, str] = {
    "denial_reason": "The letter doesn't state a specific reason. You can ask the plan in writing for the specific reason "
    "and the rule or criteria it used.",
    "appeal_instructions": "We didn't find appeal instructions. Ask the plan for its written appeal process: where to send "
    "an appeal and how.",
    "appeal_deadline": "We didn't find an appeal deadline. Ask the plan for it in writing, and don't wait to act.",
    "external_review_deadline": "The letter doesn't state an external review or fair hearing deadline. That information "
    "often arrives with the decision on an internal appeal.",
    "letter_date": "We didn't find a date. Write down the date you received the letter; deadlines often count from it.",
    "insurer_name": "We couldn't identify the insurer or administrator. Check the letterhead or your insurance card.",
    "plan_name": "We didn't find a plan name. Check your insurance card or plan documents.",
    "reference_numbers": "We didn't find a claim, member or reference number. Have your insurance card ready when you call.",
}

_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
_DATE = re.compile(rf"\b(?:(?:{_MONTHS})\s+\d{{1,2}},\s+\d{{4}}|\d{{1,2}}/\d{{1,2}}/\d{{4}})\b")
_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "ten": 10,
    "fourteen": 14,
    "fifteen": 15,
    "thirty": 30,
    "forty-five": 45,
    "sixty": 60,
    "ninety": 90,
    "one hundred eighty": 180,
}
_QTY = r"(\d{1,3}|" + "|".join(sorted(map(re.escape, _NUMBER_WORDS), key=len, reverse=True)) + r")"
_DEADLINE = re.compile(
    r"\b(?:within|no later than|not later than)\s+"
    + _QTY
    + r"\s*(?:\(\d{1,3}\)\s*)?((?:calendar|business|working)\s+)?(days?|months?|hours?|weeks?)\b"
    r"((?:\s+(?:of|from|after)\s+[^.;]{3,90})?)",
    re.I,
)
_USER_ACTION = re.compile(
    r"\b(you must|must be (?:filed|submitted|received|requested|made)|you have|you may|you can|request|submit|file|ask)\b",
    re.I,
)
_INSURER_TIMELINE = re.compile(r"\b(we will|we must|we'll|will decide|will make a decision|will notify|will respond)\b", re.I)
_EXTERNAL = re.compile(
    r"\b(external review|independent review|independent (?:external )?review organi[sz]ation|IHCAP|IURO|"
    r"fair hearing|independent health care appeals)\b",
    re.I,
)
_APPEAL = re.compile(r"\b(appeal|reconsideration|request (?:a |for )?review|grievance)\b", re.I)
_APPEAL_ACTION = re.compile(r"\b(send|submit|file|filed|call|write|fax|mail|request|ask|sending)\b", re.I)
_REASON = re.compile(
    r"\b(because|due to|reason for|not medically necessary|medical necessity|is not covered|are not covered|"
    r"does not cover|not a covered|out[- ]of[- ]network|experimental|investigational|exclu(?:ded|sion)|"
    r"more than what is needed|did not meet|does not meet|not eligible|no longer)\b",
    re.I,
)
_DECISION = re.compile(
    r"\b(denied|deny|denial|not approved|reduc(?:e|ed|ing)|terminat|stop(?:ping)?|decision|determination|"
    r"found that|not cover|does not cover|is not covered)\b",
    re.I,
)
_DENIAL_STATEMENT = re.compile(r"\b(denied|not approved|declined|reduc(?:e|ed|ing)|terminat(?:e|ed|ing)|adverse)\b", re.I)
_REASON_HEADING = re.compile(r"\b(reason|why)\b", re.I)
_REFERENCE = re.compile(
    r"\b((?:Member|Participant|Subscriber|Patient|NJ FamilyCare|Medicaid|Medicare)\s+ID(?:\s+(?:Number|No\.?|#))?|"
    r"ID\s+(?:Number|No\.?)|Group\s+(?:Number|No\.?|#)|Claim\s+(?:Number|No\.?|#|Reference|ID)|"
    r"Reference\s+(?:Number|No\.?|#)|Authorization\s+(?:Number|No\.?|#)|Case\s+(?:Number|No\.?|#)|"
    r"Policy\s+(?:Number|No\.?|#))\s*[:#]?\s*([A-Z0-9][A-Z0-9-]{3,})",
)
_PLAN_LABEL = re.compile(r"^(?:Plan(?: Name)?|Health Plan|Product|Benefit Plan)\s*:\s*(.+)$", re.I)
_INSURER_LABEL = re.compile(
    r"^(?:Insurer|Insurance Company|Carrier|Issuer|Claims Administrator|Plan Administrator|Health Plan)\s*:\s*(.+)$", re.I
)
_ORG_WORDS = re.compile(r"\b(Health|Plan|Insurance|Benefit|Benefits|Care|Partners|Mutual|Assurance|Services|Blue|Administrators?)\b")
_PLAN_PHRASE = re.compile(r"\b(?:the\s+)?([A-Z][A-Za-z0-9&.' -]{2,60}?(?:Employee Health Plan|Health Benefit Plan|PPO|HMO|EPO|POS))\b")

SUSPICIOUS = re.compile(
    r"(\b(ignore|disregard|forget)\b.{0,40}\b(previous|prior|above|earlier|all)\b.{0,25}\b(instructions?|prompts?|rules)\b|"
    r"\bnote to (automated|ai) systems?\b|\byou are (now )?(an? )?(ai|assistant|chatbot|language model)\b|"
    r"\bsystem prompt\b|<\s*/?\s*script\b|javascript:|\b(mark|treat) (this|the) (claim|appeal|request) as approved\b)",
    re.I,
)

PLAN_SIGNALS: List[Tuple[str, str, "re.Pattern[str]"]] = [
    ("self-funded", "Mentions a self-funded or self-insured plan", re.compile(r"\bself-?(funded|insured)\b", re.I)),
    ("erisa", "Mentions ERISA (usually a job-based plan)", re.compile(r"\b(ERISA|Employee Retirement Income Security Act)\b")),
    ("fully-insured", "Mentions a fully insured plan", re.compile(r"\bfully[- ]insured\b", re.I)),
    (
        "new-jersey",
        "Mentions New Jersey or NJ DOBI",
        re.compile(r"\b(issued in New Jersey|Department of Banking and Insurance|IHCAP|New Jersey)\b"),
    ),
    ("medicare", "Mentions Medicare", re.compile(r"\bMedicare\b")),
    ("medicaid", "Mentions Medicaid or NJ FamilyCare", re.compile(r"\b(Medicaid|NJ FamilyCare)\b")),
    (
        "marketplace",
        "Mentions Get Covered New Jersey or the Marketplace",
        re.compile(r"\b(Get Covered New Jersey|Health Insurance Marketplace)\b", re.I),
    ),
]
_URGENT = re.compile(r"\b(expedited|urgent)\b", re.I)


def cite(p: Passage, start: Optional[int] = None, end: Optional[int] = None) -> Citation:
    """Cite a whole passage, or a sub-span given as offsets relative to the passage."""
    a = p.start + (start or 0)
    b = p.start + (end if end is not None else len(p.text))
    return Citation(page=p.page, start=a, end=b, quote=p.text[(start or 0) : (end if end is not None else len(p.text))])


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _missing(key: FieldKey, citations: Iterable[Citation] = (), note: Optional[str] = None) -> ExtractedField:
    return ExtractedField(key=key, label=LABELS[key], status="not_found", note=note or NOT_FOUND_NOTES[key], citations=list(citations))


def _found(key: FieldKey, values: List[str], citations: List[Citation], confidence: str, **extra) -> ExtractedField:
    return ExtractedField(
        key=key,
        label=LABELS[key],
        status="found",
        value=values[0],
        values=values,
        citations=citations,
        confidence=confidence,  # type: ignore[arg-type]
        **extra,
    )


# ---------------------------------------------------------------- individual fields


def denial_reason(passages: List[Passage]) -> ExtractedField:
    content = [p for p in passages if p.kind == "sentence"]
    # Prefer sentences directly under a "Reason for ..." / "Why ..." heading.
    for i, p in enumerate(passages):
        if p.kind == "heading" and _REASON_HEADING.search(p.text):
            following = [q for q in passages[i + 1 : i + 3] if q.kind == "sentence" and q.page == p.page]
            if following and (_REASON.search(following[0].text) or _DECISION.search(following[0].text)):
                chosen = [following[0]] + [q for q in following[1:] if _REASON.search(q.text)]
                return _found("denial_reason", [_flat(q.text) for q in chosen], [cite(q) for q in chosen], "high")
    candidates = [p for p in content if _REASON.search(p.text) and _DECISION.search(p.text)]
    if candidates:
        best = candidates[0]
        return _found("denial_reason", [_flat(best.text)], [cite(best)], "medium")
    statements = [p for p in content if _DENIAL_STATEMENT.search(p.text)]
    if statements:
        return _missing(
            "denial_reason",
            [cite(statements[0])],
            "The letter says the request was not approved but doesn't explain why. You can ask the plan in writing for "
            "the specific reason and the rule or criteria it used.",
        )
    return _missing("denial_reason")


def appeal_instructions(passages: List[Passage]) -> ExtractedField:
    hits = [
        p
        for p in passages
        if p.kind == "sentence"
        and _APPEAL.search(p.text)
        and _APPEAL_ACTION.search(p.text)
        and not _EXTERNAL.search(p.text)
        and not _INSURER_TIMELINE.search(p.text)
    ][:4]
    if not hits:
        return _missing("appeal_instructions")
    return _found("appeal_instructions", [_flat(p.text) for p in hits], [cite(p) for p in hits], "high" if len(hits) > 1 else "medium")


def _deadlines(passages: List[Passage], external: bool) -> List[Tuple[Passage, "re.Match[str]"]]:
    out = []
    for p in passages:
        if p.kind != "sentence" or _INSURER_TIMELINE.search(p.text) or not _USER_ACTION.search(p.text):
            continue
        if bool(_EXTERNAL.search(p.text)) != external:
            continue
        if not external and not _APPEAL.search(p.text):
            continue
        for m in _DEADLINE.finditer(p.text):
            out.append((p, m))
    return out


def _normalize_duration(m: "re.Match[str]") -> str:
    qty_raw, qualifier, unit = m.group(1).lower(), (m.group(2) or "").strip().lower(), m.group(3).lower()
    qty = int(qty_raw) if qty_raw.isdigit() else _NUMBER_WORDS.get(qty_raw, 0)
    unit = unit if unit.endswith("s") else unit + "s"
    return f"{qty} {qualifier + ' ' if qualifier else ''}{unit}".strip()


def deadline_field(passages: List[Passage], key: FieldKey) -> ExtractedField:
    hits = _deadlines(passages, external=(key == "external_review_deadline"))
    if not hits:
        return _missing(key)
    values, citations = [], []
    for p, m in hits:
        # "within 180 days of ..." -> "180 days of ..."; other lead-ins ("no later than") are kept.
        values.append(_flat(re.sub(r"^within\s+", "", m.group(0), flags=re.I)))
        citations.append(cite(p))
    note = None
    if len(hits) > 1:
        note = "The letter lists more than one time limit. Read each one: the earliest that applies to you is the one to plan around."
    return _found(key, values, citations, "high", normalized=_normalize_duration(hits[0][1]), note=note)


def letter_date(passages: List[Passage]) -> ExtractedField:
    first_page = [p for p in passages if p.page == passages[0].page] if passages else []
    for p in first_page[:20]:
        if p.kind == "label" and p.text.lower().startswith("date"):
            m = _DATE.search(p.text)
            if m:
                return _found("letter_date", [m.group(0)], [cite(p, m.start(), m.end())], "high", normalized=_iso(m.group(0)))
    for p in first_page[:12]:
        if p.kind in {"heading", "label"}:
            m = _DATE.search(p.text)
            if m and len(p.text) < 40:
                return _found("letter_date", [m.group(0)], [cite(p, m.start(), m.end())], "medium", normalized=_iso(m.group(0)))
    return _missing("letter_date")


def _iso(raw: str) -> Optional[str]:
    for fmt in ("%B %d, %Y", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def insurer_name(passages: List[Passage]) -> ExtractedField:
    for p in passages:
        m = _INSURER_LABEL.match(_flat(p.text)) if p.kind == "label" else None
        if m:
            start = p.text.index(m.group(1)[:10]) if m.group(1)[:10] in p.text else 0
            return _found("insurer_name", [m.group(1).strip()], [cite(p, start, len(p.text))], "high")
    if passages:
        first = passages[0]
        if first.kind == "heading" and len(first.text) <= 60 and _ORG_WORDS.search(first.text) and not _DATE.search(first.text):
            return _found(
                "insurer_name", [_flat(first.text)], [cite(first)], "medium", note="Taken from the letterhead at the top of the letter."
            )
    return _missing("insurer_name")


def plan_name(passages: List[Passage]) -> ExtractedField:
    for p in passages:
        if p.kind != "label":
            continue
        m = _PLAN_LABEL.match(p.text)
        if m:
            value = m.group(1).strip()
            return _found("plan_name", [_flat(value)], [cite(p, m.start(1), m.end(1))], "high")
    for p in passages:
        if p.kind == "sentence":
            m = _PLAN_PHRASE.search(p.text)
            if m:
                return _found("plan_name", [_flat(m.group(1))], [cite(p, m.start(1), m.end(1))], "medium")
    return _missing("plan_name")


def reference_numbers(passages: List[Passage]) -> ExtractedField:
    values, citations, seen = [], [], set()
    for p in passages:
        for m in _REFERENCE.finditer(p.text):
            label = _flat(m.group(1))
            if (label, m.group(2)) in seen:
                continue
            seen.add((label, m.group(2)))
            values.append(f"{label}: {m.group(2)}")
            citations.append(cite(p, m.start(), m.end()))
    if not values:
        return _missing("reference_numbers")
    return _found("reference_numbers", values, citations, "high")


# ---------------------------------------------------------------- signals


def signals(passages: List[Passage]) -> List[Signal]:
    out: List[Signal] = []
    for code, label, pattern in PLAN_SIGNALS:
        hits = [p for p in passages if pattern.search(p.text)]
        if hits:
            out.append(Signal(kind="plan-type", code=code, label=label, citations=[cite(h) for h in hits[:3]]))
    urgent = [p for p in passages if _URGENT.search(p.text)]
    if urgent:
        out.append(
            Signal(kind="urgent", code="urgent", label="Mentions expedited or urgent appeals", citations=[cite(u) for u in urgent[:3]])
        )
    suspicious = [p for p in passages if SUSPICIOUS.search(p.text)]
    if suspicious:
        out.append(
            Signal(
                kind="suspicious",
                code="instructions-to-software",
                label="Contains text addressed to software. Medicom treats it as plain text and ignores it.",
                citations=[cite(s) for s in suspicious[:5]],
            )
        )
    return out


def extract_fields(passages: List[Passage]) -> List[ExtractedField]:
    return [
        denial_reason(passages),
        appeal_instructions(passages),
        deadline_field(passages, "appeal_deadline"),
        deadline_field(passages, "external_review_deadline"),
        letter_date(passages),
        insurer_name(passages),
        plan_name(passages),
        reference_numbers(passages),
    ]
