"""Plain-language legal statements, each tied to the verified sources that support it.

Every legal statement the app shows comes from here. Tests fail if a claim cites an unknown source.
A claim that cites a `needs-review` source is automatically flagged in API responses.
Wording is deliberately careful ("generally", "usually") where the rules have exceptions.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    source_ids: Tuple[str, ...]


_CLAIMS = [
    Claim(
        "internal_appeal_window",
        "For most job-based and individual health plans, you get at least 180 days after receiving a denial to file an internal appeal.",
        ("hcgov-internal-appeals", "cfr-29-2560-503-1"),
    ),
    Claim(
        "internal_decision_timing",
        "HealthCare.gov says an internal appeal must be decided within 30 days for care you haven’t received yet, "
        "and within 60 days for care you already received.",
        ("hcgov-internal-appeals",),
    ),
    Claim(
        "urgent_72h",
        "Under federal claims rules for employer plans, an urgent care claim must be decided as soon as possible and no later than "
        "72 hours after the plan receives it.",
        ("cfr-29-2560-503-1",),
    ),
    Claim(
        "external_review_4_months",
        "After a final internal denial, you generally have 4 months to request an independent external review.",
        ("cfr-45-147-136", "hcgov-external-review"),
    ),
    Claim(
        "external_review_binding",
        "HealthCare.gov says your insurer is required by law to accept the external reviewer’s decision.",
        ("hcgov-external-review",),
    ),
    Claim(
        "ihcap_scope",
        "New Jersey’s Independent Health Care Appeals Program (IHCAP) does not accept appeals for self-funded plans, Medicare, "
        "Medicare Advantage, or insurance contracts delivered in another state.",
        ("nj-dobi-ihcap",),
    ),
    Claim(
        "ihcap_internal_first",
        "IHCAP generally requires you to finish the plan’s internal appeal first.",
        ("nj-dobi-ihcap",),
    ),
    Claim(
        "ihcap_timing",
        "NJ DOBI says a standard IHCAP decision takes no more than 45 calendar days from when the appeal is submitted.",
        ("nj-dobi-ihcap",),
    ),
    Claim(
        "nj_dobi_hotline",
        "For problems with a New Jersey-regulated insurer, NJ DOBI’s Consumer Hotline is 1-800-446-7467.",
        ("nj-dobi-consumer",),
    ),
    Claim(
        "erisa_scope",
        "Federal claims rules for job-based plans generally apply to private-sector employer plans, with exceptions for plans "
        "sponsored by government or most religious bodies.",
        ("dol-filing-a-claim",),
    ),
    Claim(
        "erisa_appeal_window",
        "The U.S. Department of Labor says you have at least 180 days to appeal a denied claim under a private employer plan.",
        ("dol-filing-a-claim", "cfr-29-2560-503-1"),
    ),
    Claim(
        "erisa_external",
        "Job-based plans that aren’t grandfathered must provide external review of claim denials by an independent party. "
        "Plans set up after March 23, 2010, or that made certain significant changes after that date, are not grandfathered.",
        ("dol-filing-a-claim",),
    ),
    Claim(
        "medicaid_appeal_60",
        "In Medicaid managed care, you generally have 60 calendar days from the date on the notice to appeal to the plan.",
        ("cfr-42-438-subpart-f",),
    ),
    Claim(
        "medicaid_fair_hearing",
        "After the plan’s appeal decision, federal rules give at least 90 and at most 120 days to request a State fair hearing. "
        "New Jersey changed parts of its fair hearing process in 2026, so follow the deadline printed on your notice.",
        ("cfr-42-438-subpart-f", "nj-dmahs-mc-26-06"),
    ),
    Claim(
        "medicare_written",
        "If you’re in a Medicare Advantage or other Medicare plan, the plan must tell you in writing how to appeal. "
        "Medicare generally has 5 levels of appeal.",
        ("medicare-gov-appeals",),
    ),
    Claim(
        "ma_reconsideration_60",
        "In a Medicare Advantage plan, a request for reconsideration generally must be filed within 60 calendar days after you "
        "receive the plan’s written decision.",
        ("cfr-42-422-582",),
    ),
    Claim(
        "prior_auth_reason",
        "Under CMS’s prior authorization rule (CMS-0057-F), Medicare Advantage plans, Medicaid programs, and plans on the federal "
        "marketplace must give a specific reason when they deny a prior authorization request (drug requests excluded). "
        "That reason goes to your provider, so ask them for it.",
        ("cms-0057-f-fact-sheet",),
    ),
]

CLAIMS: Dict[str, Claim] = {c.id: c for c in _CLAIMS}
