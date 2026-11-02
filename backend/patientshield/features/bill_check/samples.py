"""Synthetic EOB + bill pairs for demo mode and tests.

Everything is invented: people, plans, providers, account and claim numbers. Phone numbers use the 555-01xx range
reserved for fiction. Amounts are internally consistent (allowed x 80% = plan paid; totals add up) so the
comparison is exercised on realistic numbers. ASCII only, for the minimal PDF generator.

- clean-office-visit: bill and EOB agree. Nothing to ask about.
- imaging-balance-and-repeat: an in-network imaging center bills the full charge (no network discount) and lists
  the MRI twice.
- er-visit-differences: an emergency visit where one charge differs, one bill line isn't on the EOB, and the plan
  denied one line.
"""

from dataclasses import dataclass, field
from typing import Dict, List

FOOTER = "SYNTHETIC SAMPLE - NOT A REAL BILL OR EOB - created for Medicom demo mode"


@dataclass(frozen=True)
class SampleDoc:
    id: str
    title: str
    pages: List[List[str]] = field(default_factory=list)
    footer: str = FOOTER

    @property
    def filename(self) -> str:
        return f"synthetic-{self.id}.pdf"


@dataclass(frozen=True)
class SamplePair:
    id: str
    title: str
    description: str
    eob: SampleDoc
    bill: SampleDoc


def _eob(pair_id: str, provider: str, claim: str, processed: str, rows: List[str], total: str, network: str = "In-network") -> SampleDoc:
    return SampleDoc(
        id=f"{pair_id}-eob",
        title="Explanation of Benefits",
        pages=[
            [
                "## Maplewood Health Plan",
                "P.O. Box 7700, Princeton, NJ 08540 | Member Services: (800) 555-0163",
                "## EXPLANATION OF BENEFITS - THIS IS NOT A BILL",
                f"Member: Riley Example | Member ID: MHP-209114-02 | Date processed: {processed}",
                f"Claim number: {claim} | Provider: {provider} ({network})",
                "Date Service Code Billed Allowed Plan paid You owe\n"
                + "\n".join(rows)
                + ("\n" + total if total.startswith("Total ") else ""),
                *([total] if not total.startswith("Total ") else []),
                "The amount you owe is your share of the cost under your plan. Your provider may bill you for it. "
                "If you already paid part of it at the visit, your bill should show that payment.",
                "Questions? Call Member Services at (800) 555-0163.",
            ]
        ],
    )


def _bill(
    pair_id: str, provider: str, address: str, phone: str, account: str, statement: str, rows: List[str], summary: List[str]
) -> SampleDoc:
    return SampleDoc(
        id=f"{pair_id}-bill",
        title="Patient statement",
        pages=[
            [
                f"## {provider}",
                f"{address} | Billing questions: {phone}",
                "## PATIENT STATEMENT",
                f"Patient: Riley Example | Account number: {account} | Statement date: {statement}",
                "Insurance: Maplewood Health Plan",
                "Date Code Description Charges\n" + "\n".join(rows),
                "\n".join(summary),
                f"Please pay by the due date shown on the payment slip. Questions about this bill? Call {phone}.",
            ]
        ],
    )


SAMPLE_PAIRS: List[SamplePair] = [
    SamplePair(
        id="clean-office-visit",
        title="Office visit: bill and EOB agree",
        description="A routine in-network visit with a lab test. The bill matches the EOB, so there's nothing to ask about.",
        eob=_eob(
            "clean-office-visit",
            "Riverside Family Medicine",
            "MHP-26-0902-5521",
            "September 20, 2026",
            [
                "09/02/2026 Office visit, established patient 99214 $210.00 $128.40 $102.72 $25.68",
                "09/02/2026 Comprehensive metabolic panel 80053 $64.00 $18.20 $14.56 $3.64",
            ],
            "Total $274.00 $146.60 $117.28 $29.32",
        ),
        bill=_bill(
            "clean-office-visit",
            "Riverside Family Medicine",
            "40 Example Avenue, Lawrenceville, NJ 08648",
            "(609) 555-0118",
            "RFM-0048813",
            "October 1, 2026",
            [
                "09/02/2026 99214 Office visit, established patient $210.00",
                "09/02/2026 80053 Comprehensive metabolic panel $64.00",
            ],
            ["Total charges: $274.00", "Insurance payments: -$117.28", "Adjustments: -$127.40", "Amount due: $29.32"],
        ),
    ),
    SamplePair(
        id="imaging-balance-and-repeat",
        title="Imaging center: full charge billed, MRI listed twice",
        description="An in-network imaging center bills more than the EOB says you owe, and one service appears twice on the bill.",
        eob=_eob(
            "imaging-balance-and-repeat",
            "Harborview Imaging Center",
            "MHP-26-1006-7710",
            "October 15, 2026",
            [
                "10/06/2026 Office consultation, new patient 99203 $180.00 $96.00 $76.80 $19.20",
                "10/06/2026 MRI lumbar spine without contrast 72148 $1,450.00 $612.00 $489.60 $122.40",
            ],
            "Total you owe: $141.60",
        ),
        bill=_bill(
            "imaging-balance-and-repeat",
            "Harborview Imaging Center",
            "9 Placeholder Road, Edison, NJ 08817",
            "(732) 555-0127",
            "HIC-2210457",
            "October 20, 2026",
            [
                "10/06/2026 99203 Office consultation, new patient $180.00",
                "10/06/2026 72148 MRI lumbar spine without contrast $1,450.00",
                "10/06/2026 72148 MRI lumbar spine without contrast $1,450.00",
            ],
            ["Total charges: $3,080.00", "Insurance payments: -$566.40", "Amount due: $2,513.60"],
        ),
    ),
    SamplePair(
        id="er-visit-differences",
        title="Emergency visit: a charge differs, one line missing, one denied",
        description="An emergency room visit where the CT charge differs, a medication isn't on the EOB, and the plan denied the supplies.",
        eob=_eob(
            "er-visit-differences",
            "Lakeside Regional Hospital",
            "MHP-26-0814-3307",
            "September 2, 2026",
            [
                "08/14/2026 Emergency department visit 99284 $1,980.00 $820.00 $656.00 $164.00",
                "08/14/2026 CT head without contrast 70450 $2,100.00 $540.00 $432.00 $108.00",
                "08/14/2026 Wound care supplies A6216 $95.00 $0.00 $0.00 $95.00 DENIED - not covered",
            ],
            "Total $4,175.00 $1,360.00 $1,088.00 $367.00",
        ),
        bill=_bill(
            "er-visit-differences",
            "Lakeside Regional Hospital",
            "200 Sample Boulevard, Toms River, NJ 08753",
            "(732) 555-0135",
            "LRH-77031952",
            "September 18, 2026",
            [
                "08/14/2026 99284 Emergency department visit $1,980.00",
                "08/14/2026 70450 CT head without contrast $2,250.00",
                "08/14/2026 A6216 Wound care supplies $95.00",
                "08/14/2026 J1885 Ketorolac injection, 15 mg $42.00",
            ],
            ["Total charges: $4,367.00", "Insurance payments: -$1,088.00", "Adjustments: -$2,870.00", "Amount due: $409.00"],
        ),
    ),
]

SAMPLE_PAIRS_BY_ID: Dict[str, SamplePair] = {p.id: p for p in SAMPLE_PAIRS}
