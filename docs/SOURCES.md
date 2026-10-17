# Source verification report

Last reviewed: **2026-10-17**. Registry version 1. The registry itself is in
[`backend/patientshield/sources/registry.py`](../backend/patientshield/sources/registry.py).

Federal regulations were read from the eCFR versioner API (text current as of 2026-10-15). Agency pages were read directly in a
browser. Excerpts in the registry are verbatim.

## Confirmed

| Topic | What was confirmed | Source |
| --- | --- | --- |
| ERISA claims procedure | At least 180 days to appeal; urgent claims decided within 72 hours | 29 CFR § 2560.503-1(h)(3)(i), (f)(2)(i) |
| ACA appeals & external review | 4 months to request external review; continued coverage pending appeal; not for grandfathered plans | 45 CFR § 147.136 |
| DOL guidance | Rules generally cover private-sector employer plans (exceptions for government and most religious plans); at least 180 days to appeal; non-grandfathered plans must offer independent external review | DOL EBSA, *Filing a Claim for Your Health Benefits* |
| HealthCare.gov | 180 days to file an internal appeal; 30/60-day decisions; 4 months for external review; insurer must accept the reviewer's decision | HealthCare.gov internal appeals and external review pages |
| NJ external appeal (IHCAP) | Not available for self-funded plans, Medicare or Medicare Advantage; internal appeal generally required first; standard decision within 45 calendar days; filed via Maximus | NJ DOBI IHCAP page |
| NJ DOBI consumer help | Consumer hotline 1-800-446-7467 | NJ DOBI consumer page |
| Medicaid managed care | 60 calendar days to appeal to the plan; 90–120 days to request a state fair hearing after the plan's decision | 42 CFR §§ 438.402(c)(2)(ii), 438.408(f)(2) |
| Medicare | Plan must explain in writing how to appeal; generally 5 appeal levels; MA reconsideration within 60 calendar days | Medicare.gov appeals page; 42 CFR § 422.582(b) |
| CMS-0057-F | Covers MA, Medicaid/CHIP FFS and managed care, and QHP issuers on the federal exchanges; from Jan 1, 2026 a denied prior authorization must include a specific reason in the response **to the provider**; drugs excluded | CMS fact sheet (Jan 17, 2024); 42 CFR 422.122(a), 431.80(a), 45 CFR 156.223(a) |

## Not confirmed (flagged for human review)

| Item | Why it is flagged |
| --- | --- |
| IHCAP filing deadline | The DOBI program page does not state one, and the underlying NJ statute has not been retrieved. The app will tell users to use the deadline in their final internal appeal decision. |
| CMS-0057-F and Get Covered New Jersey plans | The CMS fact sheet limits the QHP requirements to federal-exchange issuers. NJ runs its own state-based exchange, but 45 CFR 156.223(a) does not name an exchange type. Applicability to NJ marketplace plans is unconfirmed. |
| NJ FamilyCare fair hearing deadline | DMAHS Medicaid Communication 26-06 (June 23, 2026) reinstates a 20-day rule (described to beneficiaries as 30 days) and ends automatic continuation of benefits from July 1, 2026, but is addressed to eligibility agencies. An older NJ FamilyCare FAQ says 120 days after a plan appeal decision, and federal rule allows 90–120 days. Which applies to a managed care denial needs review. Users are told to follow the deadline on their notice. |

## Research statistics (README)

KFF, *Claims Denials and Appeals in ACA Marketplace Plans in 2024* (Long, Lo, Pestaina; March 24, 2026): 19% of in-network claims
denied; at least 262,982 internal appeals, an appeal rate under 1%. Scope: HealthCare.gov non-group QHPs only.
