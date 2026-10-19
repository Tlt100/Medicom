"""PatientShield verified source registry.

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

REGISTRY_VERSION = 4
LAST_REVIEWED = dt.date(2026, 10, 19)

_CHECKED = "2026-10-16"
_CHECKED_BILLS = "2026-10-19"
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
            {
                "locator": "External Appeal Review Eligibility",
                "text": "The individual is covered under a contract delivered in another state;",
            },
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
    # ------------------------------------------------------------------ Bills and Explanations of Benefits (checked 2026-10-19)
    {
        "id": "cms-read-eob",
        "title": "How to read a health insurance explanation of benefits",
        "citation": None,
        "authority": "Centers for Medicare & Medicaid Services",
        "url": "https://www.cms.gov/initiatives/your-patient-rights/medical-bill-rights/get-help/guides-resources/read-explanation-benefits",
        "jurisdiction": "US-Federal",
        "source_type": "agency-guidance",
        "topics": ["billing"],
        "date": "2026-10-05",
        "date_label": "Page last modified",
        "last_checked": _CHECKED_BILLS,
        "verification": "verified",
        "version": 1,
        "excerpts": [
            {"locator": "What’s an explanation of benefits?", "text": "An explanation of benefits isn’t a bill."},
            {
                "locator": "What’s an explanation of benefits?",
                "text": "It helps you understand how much your health plan covers, and what you’ll pay when you get a bill from your provider.",
            },
            {
                "locator": "What you owe",
                "text": "Your bill should not be higher than the Patient Balance. If it is, talk to your provider.",
            },
            {
                "locator": "What you owe",
                "text": "You may have already paid for part of the Patient Balance. The Explanation of Benefits only shows what you owe, not if you’ve already paid for it.",
            },
        ],
    },
    {
        "id": "cms-read-bill",
        "title": "How to read your medical bill",
        "citation": None,
        "authority": "Centers for Medicare & Medicaid Services",
        "url": "https://www.cms.gov/initiatives/your-patient-rights/medical-bill-rights/get-help/guides-resources/how-read-your-bill",
        "jurisdiction": "US-Federal",
        "source_type": "agency-guidance",
        "topics": ["billing"],
        "date": "2026-10-05",
        "date_label": "Page last modified",
        "last_checked": _CHECKED_BILLS,
        "verification": "verified",
        "version": 1,
        "excerpts": [
            {
                "locator": "Is a medical bill the same as an Explanation of Benefits?",
                "text": "If you don’t get an Explanation of Benefits, contact your health plan to make sure your provider’s office or facility has sent them a claim for your service or supply.",
            },
            {
                "locator": "What should I do with the Explanation of Benefits?",
                "text": "When you get a bill from your provider or facility, compare it with the Explanation of Benefits to make sure you were billed for the correct services and supplies. Also, compare the amount on your medical bill to the amount the Explanation of Benefits says you owe to make sure the amount is correct.",
            },
            {
                "locator": "What should I do with the Explanation of Benefits?",
                "text": "Only make payments after you get a bill from your provider or facility, and check to make sure that the services and amounts you owe are the same as those shown in your Explanation of Benefits.",
            },
            {
                "locator": "Who should I contact with questions about my bill?",
                "text": "If you have questions about your medical bill, or you think there’s an error on your bill or Explanation of Benefits, contact your provider or facility.",
            },
        ],
    },
    {
        "id": "cms-bill-errors",
        "title": "Check your medical bill for errors",
        "citation": None,
        "authority": "Centers for Medicare & Medicaid Services",
        "url": "https://www.cms.gov/initiatives/your-patient-rights/medical-bill-rights/get-help/guides-resources/check-your-bill-errors",
        "jurisdiction": "US-Federal",
        "source_type": "agency-guidance",
        "topics": ["billing"],
        "date": "2026-10-06",
        "date_label": "Page last modified",
        "last_checked": _CHECKED_BILLS,
        "verification": "verified",
        "version": 1,
        "excerpts": [
            {
                "locator": "How to check your bill for errors",
                "text": "Request a list of the costs for each medical item or service you’re being billed for.",
            },
            {
                "locator": "How to check your bill for errors",
                "text": "You can also ask the company for a copy of your explanation of benefits. Make sure the “your share” amount is the same as what’s on your bill.",
            },
            {"locator": "How to check your bill for errors", "text": "Make sure you weren’t billed twice for the same service."},
            {
                "locator": "How to check your bill for errors",
                "text": "Contact the billing department of each provider if you think you were double billed for a service.",
            },
        ],
    },
    {
        "id": "hcgov-balance-billing",
        "title": "Balance billing (HealthCare.gov glossary)",
        "citation": None,
        "authority": "HealthCare.gov (Centers for Medicare & Medicaid Services)",
        "url": "https://www.healthcare.gov/glossary/balance-billing/",
        "jurisdiction": "US-Federal",
        "source_type": "official-resource",
        "topics": ["billing"],
        "last_checked": _CHECKED_BILLS,
        "verification": "verified",
        "version": 1,
        "excerpts": [
            {
                "locator": "Definition",
                "text": "When a provider bills you for the difference between the provider’s charge and the allowed amount.",
            },
            {"locator": "Definition", "text": "A preferred provider may not balance bill you for covered services."},
        ],
    },
    {
        "id": "cms-nsa-insurance",
        "title": "Know your rights when using insurance (No Surprises Act)",
        "citation": None,
        "authority": "Centers for Medicare & Medicaid Services",
        "url": "https://www.cms.gov/initiatives/your-patient-rights/medical-bill-rights/know-your-rights/insurance",
        "jurisdiction": "US-Federal",
        "source_type": "agency-guidance",
        "topics": ["surprise-billing", "complaints"],
        "date": "2026-10-01",
        "date_label": "Page last modified",
        "last_checked": _CHECKED_BILLS,
        "verification": "verified",
        "review_note": "Protections depend on the type of care and setting (emergency care, care at an in-network facility, air ambulance) and generally don’t cover ground ambulance. Signing a notice and consent form can waive them for some care.",
        "version": 1,
        "excerpts": [
            {
                "locator": "Emergency room care",
                "text": "If your health insurance covers emergency care, you can't be charged any more for emergency medical services than the in-network “cost-sharing” rate by:",
            },
            {
                "locator": "What is “cost-sharing?”",
                "text": "Cost-sharing can take the form of a copayment, deductible, or coinsurance.",
            },
            {
                "locator": "Planned, non-emergency room care",
                "text": "You may lose these billing protections if you sign a notice and consent form",
            },
            {
                "locator": "If your provider isn’t following these rules",
                "text": "Have questions or want to submit a complaint over the phone? Call the No Surprises Help Desk at 1-800-985-3059",
            },
        ],
    },
    {
        "id": "nj-dobi-out-of-network",
        "title": "Out-of-network Consumer Protection, Transparency, Cost Containment, and Accountability Act",
        "citation": "P.L.2018, c.32",
        "authority": "New Jersey Department of Banking and Insurance",
        "url": "https://www.nj.gov/dobi/division_consumers/insurance/outofnetwork.html",
        "jurisdiction": "NJ",
        "source_type": "agency-guidance",
        "topics": ["surprise-billing", "complaints"],
        "last_checked": _CHECKED_BILLS,
        "verification": "verified",
        "review_note": "This is DOBI’s summary of the Act, not the statute text. It applies to plans regulated in New Jersey; self-funded plans are covered only if they opted in.",
        "version": 1,
        "excerpts": [
            {
                "locator": "Out-of-network Balance Billing Protection",
                "text": "Health care providers are prohibited from balance billing a covered person for inadvertent out-of-network services and/or out-of-network services provided on an emergency or urgent basis above the amount of the covered person’s liability for in-network cost-sharing (i.e. the covered person’s network level deductible, copayments, or coinsurance).",
            },
            {
                "locator": "Out-of-network Balance Billing Protection",
                "text": "Any attempts by the out-of-network health care provider to bill the covered person for these types of services above the covered person’s in-network cost-sharing liability should be reported to the covered person’s carrier",
            },
        ],
    },
    # ------------------------------------------------------------------ Uninsured New Jersey patients (checked 2026-10-19)
    {
        "id": "nj-pl-2008-c60",
        "title": "Limitation on hospital charges for certain uninsured patients",
        "citation": "P.L.2008, c.60 (N.J.S.A. 26:2H-12.52 and 26:2H-12.53)",
        "authority": "New Jersey Legislature",
        "url": "https://pub.njleg.gov/bills/2008/PL08/60_.HTM",
        "jurisdiction": "NJ",
        "source_type": "statute",
        "topics": ["uninsured"],
        "date": "2008-08-08",
        "date_label": "Approved",
        "last_checked": _CHECKED_BILLS,
        "verification": "needs-review",
        "review_note": "This is the law as enacted in 2008. We have not retrieved the current codified text or any later amendments, or the Department of Health’s sliding scale under N.J.S.A. 26:2H-12.53, which sets what share of the charge a patient pays. Hospital policies we saw describe the 115% cap for incomes above the Charity Care limit, but those are not official sources.",
        "version": 1,
        "excerpts": [
            {
                "locator": "Section 1 (C.26:2H-12.52)",
                "text": "A hospital licensed by the Department of Health and Senior Services pursuant to P.L.1971, c.136 (C.26:2H-1 et al.) shall charge a patient who is an uninsured resident of this State, and whose family gross income is less than 500% of the federal poverty level, an amount no greater than 115% of the applicable payment rate under the federal Medicare program, established pursuant to Pub.L.89-97 (42 U.S.C.s.1395 et seq.), for the health care services rendered to the patient.",
            },
            {
                "locator": "Section 1 (C.26:2H-12.52)",
                "text": "The amount shall be in accordance with the sliding scale based on income developed by the department pursuant to this act.",
            },
            {
                "locator": "Section 2 (C.26:2H-12.53)",
                "text": "The Department of Health and Senior Services shall establish a sliding scale based on income which stipulates the percentage of a hospital charge that an uninsured resident of this State whose family gross income is less than 500% of the federal poverty level is required to pay for health care services rendered at a hospital.",
            },
        ],
    },
    {
        "id": "nj-doh-charity-care",
        "title": "New Jersey Charity Care Fact Sheet (May 2026)",
        "citation": None,
        "authority": "New Jersey Department of Health, Office of Health Care Financing",
        "url": "https://www.nj.gov/health/hcf/documents/nj-charity-care-fact-sheet-english.pdf",
        "jurisdiction": "NJ",
        "source_type": "official-resource",
        "topics": ["uninsured"],
        "last_checked": _CHECKED_BILLS,
        "verification": "verified",
        "review_note": "The fact sheet summarizes the Hospital Care Payment Assistance Program; the regulations (N.J.A.C. 10:52) control. Hospitals decide eligibility.",
        "version": 1,
        "excerpts": [
            {
                "locator": "What is Charity Care?",
                "text": "The New Jersey Hospital Care Payment Assistance Program (Charity Care) is free or reduced charge care that is provided to patients who receive inpatient and outpatient services at acute care hospitals throughout the State of New Jersey.",
            },
            {
                "locator": "What is Charity Care?",
                "text": "Some services such as physician fees, anesthesiology fees, radiology interpretation, and outpatient prescriptions may not be covered.",
            },
            {
                "locator": "Who is eligible for Charity Care?",
                "text": "Have no health coverage or have coverage that pays only for part of the bill 2. Are ineligible for any Medicaid program coverage 3. Meet the income and asset criteria listed below.",
            },
            {
                "locator": "Income Criteria",
                "text": "less than or equal to 200% 0% greater than 200% but less than or equal to 225% 20% greater than 225% but less than or equal to 250% 40% greater than 250% but less than or equal to 275% 60% greater than 275% but less than or equal to 300% 80% greater than 300% 100%",
            },
            {
                "locator": "Assets Criteria",
                "text": "Individual assets cannot exceed $7,500 and family assets cannot exceed $15,000.",
            },
            {
                "locator": "How does someone apply for hospital care payment assistance?",
                "text": "The applicant has up to one year from the date of service to apply for hospital assistance and provide the hospital with a completed application.",
            },
            {
                "locator": "How does someone apply for hospital care payment assistance?",
                "text": "Please call the Charity Care unit during business hours at 1-866-588-5696 or 609-292-4709.",
            },
            {
                "locator": "What are the screening procedures for third party payers and Medicaid?",
                "text": "Patients should only apply for Charity Care when they are determined to be ineligible for Medicaid or any other medical assistance programs.",
            },
        ],
    },
    {
        "id": "hhs-poverty-guidelines-2026",
        "title": "HHS Poverty Guidelines for 2026",
        "citation": "91 FR 1797 (January 15, 2026)",
        "authority": "U.S. Department of Health and Human Services, ASPE",
        "url": "https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines",
        "jurisdiction": "US-Federal",
        "source_type": "agency-guidance",
        "topics": ["uninsured"],
        "date": "2026-01-13",
        "date_label": "Effective date (Federal Register notice)",
        "last_checked": _CHECKED_BILLS,
        "verification": "verified",
        "review_note": "Figures are for the 48 contiguous states and DC. A program can set its own effective date for new guidelines, and a hospital may use the guidelines in effect on your date of service.",
        "version": 1,
        "excerpts": [
            {
                "locator": "2026 poverty guidelines, 48 contiguous states and DC",
                "text": "2026 POVERTY GUIDELINES FOR THE 48 CONTIGUOUS STATES AND THE DISTRICT OF COLUMBIA Persons in family/household Poverty guideline 1 $15,960 2 $21,640 3 $27,320 4 $33,000 5 $38,680 6 $44,360 7 $50,040 8 $55,720",
            },
            {
                "locator": "2026 poverty guidelines, 48 contiguous states and DC",
                "text": "For families/households with more than 8 persons, add $5,680 for each additional person.",
            },
        ],
    },
    {
        "id": "fr-2026-00755",
        "title": "Annual Update of the HHS Poverty Guidelines (Federal Register notice)",
        "citation": "91 FR 1797; FR Doc. 2026-00755",
        "authority": "U.S. Department of Health and Human Services, Office of the Secretary",
        "url": "https://www.govinfo.gov/content/pkg/FR-2026-01-15/pdf/2026-00755.pdf",
        "jurisdiction": "US-Federal",
        "source_type": "agency-guidance",
        "topics": ["uninsured"],
        "date": "2026-01-15",
        "date_label": "Published",
        "last_checked": _CHECKED_BILLS,
        "verification": "verified",
        "version": 1,
        "excerpts": [
            {
                "locator": "DATES",
                "text": "Effective Date: January 13, 2026 unless an office administering a program using the guidelines specifies a different effective date for that particular program.",
            },
            {
                "locator": "2026 poverty guidelines, 48 contiguous states and DC",
                "text": "1 .................................................. $15,960",
            },
        ],
    },
    {
        "id": "cms-medical-bill-rights",
        "title": "Medical bill rights",
        "citation": None,
        "authority": "Centers for Medicare & Medicaid Services",
        "url": "https://www.cms.gov/initiatives/your-patient-rights/medical-bill-rights",
        "jurisdiction": "US-Federal",
        "source_type": "agency-guidance",
        "topics": ["uninsured", "billing"],
        "date": "2026-10-05",
        "date_label": "Page last modified",
        "last_checked": _CHECKED_BILLS,
        "verification": "verified",
        "version": 1,
        "excerpts": [
            {
                "locator": "What is the No Surprises Act?",
                "text": "Usually, if you don't have or use health insurance, providers must give you a good faith estimate of what your care will cost. You get the estimate when you schedule care in advance or if you ask for one. You may be able to dispute your bill if it’s at least $400 more than the estimate.",
            },
        ],
    },
]
