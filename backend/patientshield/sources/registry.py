"""PatientShield verified source registry (NJ Denial Navigator MVP).

RULES FOR EDITING
- Excerpt `text` is copied verbatim from `url` on `last_checked`. Never paraphrase inside it.
- Only set `date` when the source itself showed it, and label what kind of date it is.
- Anything confirmed only through secondary sources, or that conflicts with another source,
  is `needs-review` with a `review_note`. The app never presents those as fact.
- Bump REGISTRY_VERSION and the entry's `version` whenever an entry changes.

Federal regulation text was retrieved from the eCFR versioner API (current as of 2026-10-15).
"""

import datetime as dt
from typing import Any, Dict, List

REGISTRY_VERSION = 2
LAST_REVIEWED = dt.date(2026, 10, 17)

_CHECKED = "2026-10-16"
_ECFR = {"date": "2026-10-15", "date_label": "eCFR text current as of"}

RAW_SOURCES: List[Dict[str, Any]] = [
    # ------------------------------------------------------------------ Federal: private plans
    {
        "id": "cfr-29-2560-503-1",
        "title": "Claims procedure for employee benefit plans (ERISA)",
        "citation": "29 CFR § 2560.503-1",
        "authority": "U.S. Department of Labor, Employee Benefits Security Administration",
        "url": "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XXV/subchapter-G/part-2560/section-2560.503-1",
        "jurisdiction": "US-Federal",
        "source_type": "regulation",
        "topics": ["internal-appeal", "urgent", "plan-type"],
        **_ECFR,
        "last_checked": _CHECKED,
        "verification": "verified",
        "version": 1,
        "excerpts": [
            {
                "locator": "§ 2560.503-1(h)(3)(i)",
                "text": "Provide claimants at least 180 days following receipt of a notification of an adverse benefit determination within which to appeal the determination;",
            },
            {
                "locator": "§ 2560.503-1(f)(2)(i)",
                "text": "In the case of a claim involving urgent care, the plan administrator shall notify the claimant of the plan's benefit determination (whether adverse or not) as soon as possible, taking into account the medical exigencies, but not later than 72 hours after receipt of the claim by the plan",
            },
        ],
    },
    {
        "id": "cfr-45-147-136",
        "title": "Internal claims and appeals and external review processes (Affordable Care Act)",
        "citation": "45 CFR § 147.136",
        "authority": "U.S. Department of Health and Human Services",
        "url": "https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-B/part-147/section-147.136",
        "jurisdiction": "US-Federal",
        "source_type": "regulation",
        "topics": ["internal-appeal", "external-review"],
        **_ECFR,
        "last_checked": _CHECKED,
        "verification": "verified",
        "review_note": "Does not apply to grandfathered health plans. Whether the state or federal external review process applies depends on plan type.",
        "version": 1,
        "excerpts": [
            {
                "locator": "§ 147.136(d)(2)(i)",
                "text": "A group health plan or health insurance issuer must allow a claimant to file a request for an external review with the plan or issuer if the request is filed within four months after the date of receipt of a notice of an adverse benefit determination or final internal adverse benefit determination.",
            },
            {
                "locator": "§ 147.136(b)(2)(iii)",
                "text": "A plan and issuer subject to the requirements of this paragraph (b)(2) are required to provide continued coverage pending the outcome of an appeal.",
            },
        ],
    },
    {
        "id": "dol-filing-a-claim",
        "title": "Filing a Claim for Your Health Benefits",
        "authority": "U.S. Department of Labor, Employee Benefits Security Administration",
        "url": "https://www.dol.gov/agencies/ebsa/about-ebsa/our-activities/resource-center/publications/filing-a-claim-for-your-health-benefits",
        "jurisdiction": "US-Federal",
        "source_type": "agency-guidance",
        "topics": ["internal-appeal", "external-review", "plan-type"],
        "last_checked": _CHECKED,
        "verification": "verified",
        "version": 2,
        "excerpts": [
            {
                "locator": "Introduction",
                "text": "generally apply to people who receive health benefits from a private-sector employment plan",
            },
            {
                "locator": "Introduction",
                "text": "However, there are exceptions for plans sponsored by government or most religious bodies.",
            },
            {"locator": "Appeals", "text": "Whatever the reason, you have at least 180 days to file an appeal"},
            {
                "locator": "Additional Rules for Plans Not Grandfathered under the Affordable Care Act",
                "text": "Plans that are not grandfathered are those established, or that have made certain significant changes, after March 23, 2010.",
            },
            {
                "locator": "Additional Rules for Plans Not Grandfathered under the Affordable Care Act",
                "text": "plans that are not grandfathered under the Affordable Care Act must provide for external review of claim denials by an independent party.",
            },
        ],
    },
    {
        "id": "hcgov-internal-appeals",
        "title": "Internal appeals",
        "authority": "HealthCare.gov (Centers for Medicare & Medicaid Services)",
        "url": "https://www.healthcare.gov/appeal-insurance-company-decision/internal-appeals/",
        "jurisdiction": "US-Federal",
        "source_type": "educational",
        "topics": ["internal-appeal"],
        "last_checked": _CHECKED,
        "verification": "verified",
        "version": 1,
        "excerpts": [
            {
                "locator": "Filing deadline",
                "text": "You must file your internal appeal within 180 days (6 months) of receiving notice that your claim was denied.",
            },
            {
                "locator": "Decision timing",
                "text": "Your internal appeal must be completed within 30 days if your appeal is for a service you haven’t received yet.",
            },
            {
                "locator": "Decision timing",
                "text": "Your internal appeals must be completed within 60 days if your appeal is for a service you’ve already received.",
            },
        ],
    },
    {
        "id": "hcgov-external-review",
        "title": "External review",
        "authority": "HealthCare.gov (Centers for Medicare & Medicaid Services)",
        "url": "https://www.healthcare.gov/appeal-insurance-company-decision/external-review/",
        "jurisdiction": "US-Federal",
        "source_type": "educational",
        "topics": ["external-review"],
        "last_checked": _CHECKED,
        "verification": "verified",
        "version": 1,
        "excerpts": [
            {"locator": "Filing deadline", "text": "within 4 months after the date you receive a notice or final determination"},
            {"locator": "Binding decision", "text": "Your insurer is required by law to accept the external reviewer’s decision."},
        ],
    },
    # ------------------------------------------------------------------ New Jersey: insurance
    {
        "id": "nj-dobi-ihcap",
        "title": "Independent Health Care Appeals Program (IHCAP)",
        "authority": "New Jersey Department of Banking and Insurance",
        "url": "https://www.nj.gov/dobi/division_insurance/managedcare/ihcap.htm",
        "jurisdiction": "NJ",
        "source_type": "official-resource",
        "topics": ["external-review", "plan-type"],
        "last_checked": _CHECKED,
        "verification": "verified",
        "review_note": "The program page does not state a filing deadline. We have not retrieved the underlying NJ statute. Use the deadline in the final internal appeal decision and confirm with NJ DOBI.",
        "version": 1,
        "excerpts": [
            {
                "locator": "External Appeal Review Eligibility",
                "text": "Appeals under the IHCAP are not eligible for review if: The individual is covered under a self-funded insurance plan, Medicare, or a Medicare Advantage product;",
            },
            {"locator": "External Appeal Review Eligibility", "text": "The individual is covered under a contract delivered in another state;"},
            {"locator": "External Appeal Review Eligibility", "text": "The internal appeal process has not been completed"},
            {
                "locator": "Decision timing",
                "text": "this will not be more than 45 calendar days from when your request for an appeal was submitted.",
            },
            {"locator": "Contact", "text": "1-888-393-1062 or 609-777-9470"},
        ],
    },
    {
        "id": "nj-dobi-consumer",
        "title": "Consumer Assistance & Insurance Complaints",
        "authority": "New Jersey Department of Banking and Insurance",
        "url": "https://www.nj.gov/dobi/consumer.htm",
        "jurisdiction": "NJ",
        "source_type": "official-resource",
        "topics": ["complaints"],
        "last_checked": _CHECKED,
        "verification": "verified",
        "version": 1,
        "excerpts": [{"locator": "Consumer Hotline", "text": "1-800-446-7467"}],
    },
    # ------------------------------------------------------------------ Medicaid / NJ FamilyCare
    {
        "id": "cfr-42-438-subpart-f",
        "title": "Medicaid managed care grievance and appeal system",
        "citation": "42 CFR §§ 438.402, 438.408",
        "authority": "Centers for Medicare & Medicaid Services",
        "url": "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-438/subpart-F",
        "jurisdiction": "US-Federal",
        "source_type": "regulation",
        "topics": ["medicaid", "internal-appeal"],
        **_ECFR,
        "last_checked": _CHECKED,
        "verification": "verified",
        "version": 1,
        "excerpts": [
            {
                "locator": "§ 438.402(c)(2)(ii)",
                "text": "Following receipt of a notification of an adverse benefit determination by an MCO, PIHP, or PAHP, an enrollee has 60 calendar days from the date on the adverse benefit determination notice in which to file a request for an appeal to the managed care plan.",
            },
            {
                "locator": "§ 438.408(f)(2)",
                "text": "The enrollee must have no less than 90 calendar days and no more than 120 calendar days from the date of the MCO's, PIHP's, or PAHP's notice of resolution to request a State fair hearing.",
            },
        ],
    },
    {
        "id": "nj-dmahs-mc-26-06",
        "title": "Medicaid Communication No. 26-06: Operational Changes to Medicaid Fair Hearing Process",
        "authority": "NJ Department of Human Services, Division of Medical Assistance and Health Services",
        "url": "https://www.nj.gov/humanservices/dmahs/documents/providers-stakeholders/resources/medicaid/2026/26-06_Operational_Changes_to_Fair_Hearing_Process.pdf",
        "jurisdiction": "NJ",
        "source_type": "agency-guidance",
        "topics": ["medicaid"],
        "date": "2026-06-23",
        "date_label": "Communication dated",
        "last_checked": _CHECKED,
        "verification": "needs-review",
        "review_note": "This June 2026 communication changes fair hearing timing and continuation of benefits effective July 1, 2026. It is addressed to eligibility agencies, and an older NJ FamilyCare FAQ gives a different (120-day) window for plan appeal decisions. Which deadline applies to a managed care denial needs human review. Users are told to follow the deadline on their notice.",
        "version": 1,
        "excerpts": [
            {
                "locator": "Subject line",
                "text": "Operational Changes to Medicaid Fair Hearing Process Effective July 1, 2026",
            }
        ],
    },
    # ------------------------------------------------------------------ Medicare
    {
        "id": "medicare-gov-appeals",
        "title": "Filing an appeal",
        "authority": "Medicare.gov (Centers for Medicare & Medicaid Services)",
        "url": "https://www.medicare.gov/providers-services/claims-appeals-complaints/appeals",
        "jurisdiction": "US-Federal",
        "source_type": "official-resource",
        "topics": ["medicare"],
        "last_checked": _CHECKED,
        "verification": "verified",
        "version": 1,
        "excerpts": [
            {"locator": "Before you start", "text": "The plan must tell you, in writing, how to appeal."},
            {
                "locator": "How do appeals work?",
                "text": "Generally, there are 5 levels of appeals. If you disagree with the decision made at any level of the process, you can usually go to the next level.",
            },
        ],
    },
    {
        "id": "cfr-42-422-582",
        "title": "Request for a standard reconsideration (Medicare Advantage)",
        "citation": "42 CFR § 422.582",
        "authority": "Centers for Medicare & Medicaid Services",
        "url": "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-422/subpart-M/section-422.582",
        "jurisdiction": "US-Federal",
        "source_type": "regulation",
        "topics": ["medicare"],
        **_ECFR,
        "last_checked": _CHECKED,
        "verification": "verified",
        "version": 1,
        "excerpts": [
            {
                "locator": "§ 422.582(b)",
                "text": "a request for reconsideration must be filed within 60 calendar days after receipt of the written organization determination notice.",
            }
        ],
    },
    # ------------------------------------------------------------------ Prior authorization
    {
        "id": "cms-0057-f-fact-sheet",
        "title": "CMS Interoperability and Prior Authorization Final Rule (CMS-0057-F)",
        "citation": "CMS-0057-F; see 42 CFR 422.122(a), 42 CFR 431.80(a), 45 CFR 156.223(a)",
        "authority": "Centers for Medicare & Medicaid Services",
        "url": "https://www.cms.gov/newsroom/fact-sheets/cms-interoperability-prior-authorization-final-rule-cms-0057-f",
        "jurisdiction": "US-Federal",
        "source_type": "agency-guidance",
        "topics": ["denial-notice", "medicare", "medicaid"],
        "date": "2024-01-17",
        "date_label": "Fact sheet published",
        "last_checked": _CHECKED,
        "verification": "verified",
        "review_note": "The rule covers QHP issuers on the Federally Facilitated Exchanges. New Jersey runs its own state-based exchange (Get Covered New Jersey), so whether these requirements reach NJ marketplace plans is unconfirmed. The denial-reason requirement is for the response to the provider, excludes drugs, and does not cover employer or self-funded plans.",
        "version": 1,
        "excerpts": [
            {
                "locator": "Introduction",
                "text": "Medicare Advantage (MA) organizations, state Medicaid and Children’s Health Insurance Program (CHIP) Fee-for-Service (FFS) programs, Medicaid managed care plans, CHIP managed care entities, and Qualified Health Plan (QHP) issuers on the Federally Facilitated Exchanges (FFEs), (collectively “impacted payers”)",
            },
            {
                "locator": "Prior Authorization API",
                "text": "denies the prior authorization request (and a specific reason for the denial)",
            },
            {
                "locator": "Introduction",
                "text": "Impacted payers must also implement certain operational provisions, generally beginning January 1, 2026.",
            },
        ],
    },
]
