"""Reads service rows and totals from an EOB or a bill.

Rules, not guesses:
- A service row is a line that starts with a date of service and contains at least one dollar amount.
- Amount columns are named from the table's header line ("Billed  Allowed  Plan paid  You owe"). If the header
  can't be read, or a row has a different number of amounts than the header has columns, the row is still listed
  but its amounts are left unlabelled and a warning says so. A bill row with a single amount is its charge.
- Totals come from labelled lines such as "Amount due: $73.40" or a "Total" row under the table.
Every row and total cites its exact line on the page.
"""

import datetime as dt
import re
from typing import Dict, Iterator, List, Optional, Tuple

from patientshield.core.citations import DocumentCitation
from patientshield.features.bill_check.models import ColumnKey, LineItem, Total, TotalKey

MONEY = re.compile(r"\(?-?\$\s?-?\d{1,3}(?:,\d{3})*\.\d{2}\)?|\(?-?\b\d{1,3}(?:,\d{3})*\.\d{2}\b\)?")
DATE = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})\b")
CODE = re.compile(r"\b(\d{5}|[A-V]\d{4})\b")
DENIED = re.compile(r"\b(denied|not covered|not payable)\b", re.I)

# Header words for each column, longest first so "plan paid" wins over "paid".
HEADER_WORDS: List[Tuple[str, ColumnKey]] = [
    ("patient responsibility", "patient_owes"),
    ("your responsibility", "patient_owes"),
    ("insurance payment", "plan_paid"),
    ("paid by insurer", "plan_paid"),
    ("provider charges", "billed"),
    ("patient balance", "patient_owes"),
    ("amount billed", "billed"),
    ("paid by plan", "plan_paid"),
    ("insurance paid", "plan_paid"),
    ("patient paid", "patient_paid"),
    ("not covered", "not_covered"),
    ("coinsurance", "coinsurance"),
    ("your share", "patient_owes"),
    ("deductible", "deductible"),
    ("adjustment", "adjustment"),
    ("negotiated", "allowed"),
    ("plan paid", "plan_paid"),
    ("plan pays", "plan_paid"),
    ("you owe", "patient_owes"),
    ("allowed", "allowed"),
    ("eligible", "allowed"),
    ("charges", "billed"),
    ("balance", "balance"),
    ("charge", "billed"),
    ("billed", "billed"),
    ("copay", "copay"),
    ("amount", "billed"),
]

TOTAL_LABELS: List[Tuple[re.Pattern, TotalKey, str]] = [
    (
        re.compile(r"^\s*(total (you owe|patient responsibility|your share)|what you owe|you may owe)\b", re.I),
        "patient_owes",
        "What the EOB says you owe",
    ),
    (
        re.compile(r"^\s*(amount due|balance due|total due|please pay|pay this amount|patient balance due)\b", re.I),
        "amount_due",
        "Amount due on the bill",
    ),
    (re.compile(r"^\s*total charges\b", re.I), "total_charges", "Total charges"),
    (re.compile(r"^\s*(insurance (payments?|paid)|paid by (your )?(plan|insurance))\b", re.I), "insurance_paid", "Insurance payments"),
    (re.compile(r"^\s*(adjustments?|discounts?)\b", re.I), "adjustments", "Adjustments"),
    (re.compile(r"^\s*(patient payments?|payments? received|you paid)\b", re.I), "patient_paid", "Your payments"),
]


def cents(token: str) -> int:
    negative = token.startswith("(") or "-" in token
    digits = re.sub(r"[^\d]", "", token)
    value = int(digits)
    return -value if negative else value


def iso_date(m: re.Match) -> Optional[str]:
    month, day, year = int(m.group(1)), int(m.group(2)), m.group(3)
    full_year = int(year) + 2000 if len(year) == 2 else int(year)
    try:
        return dt.date(full_year, month, day).isoformat()
    except ValueError:
        return None


def _lines(pages: List[str]) -> Iterator[Tuple[int, int, int, str]]:
    """Yields (page number, start, end, text) for every non-blank line, with exact offsets into the page text."""
    for number, text in enumerate(pages, start=1):
        for m in re.finditer(r"[^\n]+", text):
            stripped = m.group(0).strip()
            if stripped:
                lead = len(m.group(0)) - len(m.group(0).lstrip())
                start = m.start() + lead
                yield number, start, start + len(stripped), stripped


def header_columns(line: str) -> List[ColumnKey]:
    """Column keys in the order their header words appear in the line."""
    lower = line.lower()
    taken = [False] * len(lower)
    found: List[Tuple[int, ColumnKey]] = []
    for word, key in HEADER_WORDS:
        for m in re.finditer(r"\b" + re.escape(word) + r"\b", lower):
            if any(taken[m.start() : m.end()]):
                continue
            for i in range(m.start(), m.end()):
                taken[i] = True
            found.append((m.start(), key))
    return [key for _, key in sorted(found)]


def _is_header(line: str) -> bool:
    """A table header: no amounts, short, names at least one column and says what the rows are (date, service, code)."""
    if MONEY.search(line) or len(line.split()) > 14:
        return False
    return bool(header_columns(line)) and bool(re.search(r"\b(date|service|description|code|cpt)\b", line, re.I))


def read_line_items(pages: List[str], prefix: str, doc_type: str) -> Tuple[List[ColumnKey], List[LineItem], List[Total], List[str]]:
    columns: List[ColumnKey] = []
    items: List[LineItem] = []
    totals: List[Total] = []
    warnings: List[str] = []
    unlabelled = 0
    seen_totals: Dict[str, bool] = {}

    for page, start, end, line in _lines(pages):
        citation = DocumentCitation(page=page, start=start, end=end, quote=pages[page - 1][start:end])
        amounts = MONEY.findall(line)

        if _is_header(line):
            columns = header_columns(line)
            continue

        date = DATE.match(line)
        if date and amounts:
            rest = line[date.end() :]
            first_money = MONEY.search(rest)
            middle = rest[: first_money.start()] if first_money else rest
            code_match = CODE.search(middle)
            code = code_match.group(1) if code_match else None
            description = (middle[: code_match.start()] + middle[code_match.end() :]) if code_match else middle
            description = re.sub(r"\s+", " ", description).strip(" -:|") or "Service"
            values = [cents(a) for a in amounts]
            labelled: Dict[ColumnKey, int] = {}
            if columns and len(values) == len(columns):
                labelled = dict(zip(columns, values, strict=True))
            elif doc_type == "bill" and len(values) == 1:
                labelled = {"billed": values[0]}
            else:
                unlabelled += 1
            items.append(
                LineItem(
                    id=f"{prefix}-{len(items) + 1}",
                    service_date=iso_date(date),
                    code=code,
                    description=description[:200],
                    amounts=labelled,
                    status="denied" if DENIED.search(line) else "listed",
                    citation=citation,
                )
            )
            continue

        # A "Total" row under the table, lined up with its columns.
        if re.match(r"^\s*totals?\b", line, re.I) and columns and len(amounts) == len(columns) and len(amounts) > 1:
            row = dict(zip(columns, (cents(a) for a in amounts), strict=True))
            if "patient_owes" in row and "patient_owes" not in seen_totals:
                totals.append(
                    Total(key="patient_owes", label="What the EOB says you owe", amount_cents=row["patient_owes"], citation=citation)
                )
                seen_totals["patient_owes"] = True
            continue

        if len(amounts) >= 1:
            for pattern, key, label in TOTAL_LABELS:
                if pattern.search(line) and key not in seen_totals:
                    totals.append(Total(key=key, label=label, amount_cents=cents(amounts[-1]), citation=citation))
                    seen_totals[key] = True
                    break

    if unlabelled:
        warnings.append(
            f"We couldn't tell which column {'an amount' if unlabelled == 1 else 'some amounts'} belonged to on "
            f"{unlabelled} {'row' if unlabelled == 1 else 'rows'}, so those amounts aren't compared. Check them against the original."
        )
    return columns, items, totals, warnings
