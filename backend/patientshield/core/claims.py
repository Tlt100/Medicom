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
    # ---------------------------------------------------------------- uninsured New Jersey patients
    Claim(
        "nj_uninsured_cap",
        "A 2008 New Jersey law (P.L.2008, c.60) says a licensed NJ hospital may charge an uninsured NJ resident whose family "
        "gross income is less than 500% of the federal poverty level no more than 115% of the applicable Medicare payment rate "
        "for the care.",
        ("nj-pl-2008-c60",),
    ),
    Claim(
        "nj_uninsured_sliding_scale",
        "The same law directs the NJ Department of Health to set an income-based sliding scale for what these patients pay. "
        "We haven’t confirmed that scale, so ask the hospital how it applies the law to your bill.",
        ("nj-pl-2008-c60",),
    ),
    Claim(
        "charity_care_what",
        "New Jersey Charity Care (the Hospital Care Payment Assistance Program) is free or reduced-charge care for necessary "
        "inpatient and outpatient services at NJ acute care hospitals. It isn’t health insurance.",
        ("nj-doh-charity-care",),
    ),
    Claim(
        "charity_care_who",
        "Charity Care is for NJ residents who have no health coverage (or coverage that pays only part of the bill), aren’t "
        "eligible for Medicaid, and meet income and asset limits.",
        ("nj-doh-charity-care",),
    ),
    Claim(
        "charity_care_income",
        "Under Charity Care, a patient whose income is at or below 200% of the HHS poverty guidelines pays 0% of the charge. "
        "Above 200% and up to 300%, the patient pays 20%, 40%, 60% or 80% of the charge, in income bands that end at 225%, "
        "250%, 275% and 300%. Above 300%, the patient pays 100%.",
        ("nj-doh-charity-care",),
    ),
    Claim(
        "charity_care_assets",
        "Charity Care also has asset limits: $7,500 for an individual and $15,000 for a family. Assets above the limit can be "
        "spent down on the hospital bill.",
        ("nj-doh-charity-care",),
    ),
    Claim(
        "charity_care_apply",
        "You apply for Charity Care at the hospital that treated you, at its business or admissions office, and you have up to "
        "one year from the date of service. You’ll need proof of income, assets and NJ residency.",
        ("nj-doh-charity-care",),
    ),
    Claim(
        "charity_care_medicaid_first",
        "The hospital first screens you for Medicaid and other programs. Charity Care is for people who aren’t eligible for them.",
        ("nj-doh-charity-care",),
    ),
    Claim(
        "charity_care_not_everything",
        "Charity Care may not cover physician fees, anesthesiology, radiology interpretation or outpatient prescriptions, which "
        "are often billed separately.",
        ("nj-doh-charity-care",),
    ),
    Claim(
        "charity_care_hotline",
        "The NJ Department of Health’s Charity Care unit answers questions at 1-866-588-5696 or 609-292-4709.",
        ("nj-doh-charity-care",),
    ),
    Claim(
        "poverty_guidelines_2026",
        "The 2026 HHS poverty guideline for the 48 contiguous states and DC is $15,960 for one person, plus $5,680 for each "
        "additional person. Some programs use a different effective date.",
        ("hhs-poverty-guidelines-2026", "fr-2026-00755"),
    ),
    Claim(
        "good_faith_estimate",
        "If you don’t have or use insurance, providers usually must give you a good faith estimate when you schedule care in "
        "advance or ask for one. You may be able to dispute a bill that’s at least $400 more than the estimate.",
        ("cms-medical-bill-rights",),
    ),
    # ---------------------------------------------------------------- price context
    Claim(
        "medicare_estimate_how",
        "PatientShield’s Medicare estimates follow CMS’s 2026 physician fee schedule formula: each service’s relative value "
        "units, adjusted for New Jersey costs, times the conversion factor. CMS set the 2026 conversion factor at $33.40 for "
        "most clinicians.",
        ("cms-pfs-rvu26d", "cms-pfs-2026-final-rule"),
    ),
    Claim(
        "medicare_facility_rate",
        "CMS uses a separate facility rate for services in hospitals, emergency rooms, skilled nursing facilities and surgery "
        "centers, and a non-facility rate everywhere else, such as a doctor’s office.",
        ("cms-pfs-rvu26d",),
    ),
    Claim(
        "price_transparency_list",
        "Federal rules require hospitals to publish online a list of their standard charges for all items and services.",
        ("cfr-45-180",),
    ),
    Claim(
        "price_transparency_shoppable",
        "Hospitals must also show prices for at least 300 shoppable services in a consumer-friendly way, or offer an online "
        "price estimator.",
        ("cfr-45-180",),
    ),
    Claim(
        "price_terms",
        "In those lists, the gross charge is the hospital’s chargemaster price before any discounts, and the discounted cash "
        "price is what applies to someone paying cash.",
        ("cfr-45-180",),
    ),
]

CLAIMS: Dict[str, Claim] = {c.id: c for c in _CLAIMS}
