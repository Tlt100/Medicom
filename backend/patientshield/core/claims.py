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
        "ihcap_contact",
        "NJ DOBI lists 1-888-393-1062 or 609-777-9470 for questions about the Independent Health Care Appeals Program.",
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
    # ---------------------------------------------------------------- bills and EOBs
    Claim(
        "eob_not_a_bill",
        "CMS says an Explanation of Benefits (EOB) isn’t a bill. It shows how much your plan covers and what you’ll pay "
        "when you get a bill from your provider.",
        ("cms-read-eob",),
    ),
    Claim(
        "bill_not_above_eob",
        "CMS says your bill should not be higher than the amount your EOB says you owe (the patient balance). If it is, talk to "
        "your provider.",
        ("cms-read-eob", "cms-bill-errors"),
    ),
    Claim(
        "eob_may_not_show_payments",
        "An EOB shows what you owe, not whether you already paid part of it, for example a copay at the visit.",
        ("cms-read-eob",),
    ),
    Claim(
        "compare_before_paying",
        "CMS suggests comparing your bill with your EOB, both the services and the amount you owe, and paying only after you’ve "
        "checked that they match.",
        ("cms-read-bill",),
    ),
    Claim(
        "missing_eob_ask_plan",
        "If you don’t get an EOB for a service, CMS suggests asking your health plan whether the provider sent them a claim for it.",
        ("cms-read-bill",),
    ),
    Claim(
        "billed_twice",
        "CMS suggests checking that you weren’t billed twice for the same service, and contacting the provider’s billing "
        "department if you think you were.",
        ("cms-bill-errors",),
    ),
    Claim(
        "ask_itemized_bill",
        "CMS suggests asking the provider’s billing department for a list of the costs for each item or service you’re being billed for.",
        ("cms-bill-errors",),
    ),
    Claim(
        "billing_questions_contact_provider",
        "For questions about a bill, or an error on your bill or EOB, CMS says to contact your provider or facility.",
        ("cms-read-bill",),
    ),
    Claim(
        "in_network_no_balance_bill",
        "HealthCare.gov says a preferred (in-network) provider may not balance bill you for covered services, meaning bill you "
        "for the difference between its charge and the plan’s allowed amount.",
        ("hcgov-balance-billing",),
    ),
    Claim(
        "nsa_emergency",
        "Under the federal No Surprises Act, if your plan covers emergency care, you generally can’t be charged more for "
        "emergency services than your in-network cost-sharing (copayment, deductible or coinsurance). Some protections depend "
        "on the setting and can be waived by signing a consent form for some non-emergency care.",
        ("cms-nsa-insurance",),
    ),
    Claim(
        "nsa_help_desk",
        "For questions or complaints about surprise bills, the federal No Surprises Help Desk is 1-800-985-3059.",
        ("cms-nsa-insurance",),
    ),
    Claim(
        "nj_out_of_network",
        "For plans regulated in New Jersey, NJ DOBI says providers can’t bill you above your in-network cost-sharing for "
        "emergency or urgent care, or for inadvertent out-of-network care at an in-network facility (P.L.2018, c.32). "
        "Report such a bill to your insurer.",
        ("nj-dobi-out-of-network",),
    ),
]

CLAIMS: Dict[str, Claim] = {c.id: c for c in _CLAIMS}
