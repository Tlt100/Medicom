# PatientShield

[![CI](https://github.com/Tlt100/Medicom/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Tlt100/Medicom/actions/workflows/ci.yml)

**Understand your insurance denial, line by line.** PatientShield reads a health insurance denial letter, shows exactly where each
detail appears, and explains which New Jersey or federal rules apply to the reader's type of plan, with a source for every claim.

**Live demo:** https://medicom-one.vercel.app

> **Portfolio prototype.** It uses synthetic sample letters only and is **not approved for real protected health information**.
> It is an educational tool, not legal advice, and does not claim HIPAA compliance.

## The problem

Denials are common and appeals are rare. In 2024, insurers selling plans on HealthCare.gov denied **19% of in-network claims**, and
consumers appealed **less than 1%** of those denials
([KFF, *Claims Denials and Appeals in ACA Marketplace Plans in 2024*, March 24, 2026](https://www.kff.org/patient-consumer-protections/claims-denials-and-appeals-in-aca-marketplace-plans-in-2024/)).
That data covers HealthCare.gov marketplace plans only. It excludes state-based marketplaces such as New Jersey's, and employer plans,
so it is context, not a New Jersey figure.

Existing tools mostly help write persuasive appeal letters. PatientShield focuses on the step before that, **understanding**:

1. What does the denial letter actually say? (quoted, with page numbers)
2. Which rules apply to *this* plan? (NJ-regulated, self-funded/ERISA, marketplace, Medicaid, Medicare, or unknown)
3. What are the verified next steps, and which official body can help?

The tone is calm and neutral. The goal is member clarity, not an adversarial stance toward insurers or providers.

## Status

| Milestone | Scope | Status |
| --- | --- | --- |
| 1 | Runnable skeleton, landing page, verified source registry API, deploy pipeline | **Done** |
| 2 | Synthetic letters + extraction (reason, instructions, deadline, plan/insurer, reference numbers), page-linked citations | **Done** |
| 3 | Plan-type triage flow with cited rules for each plan type | **Done** |
| 4 | Action plan: letter and rules side by side, computed deadlines, cited checklist, documents, questions, contacts, print | **Done** |
| 5 | Source library: filters and search, verbatim excerpts, review flags, re-check dates, statements citing each source | **Done** |
| Expansion, step 2 | Shared core (document pipeline with document types, citations, sources, triage) + feature modules; denials moved into `features/denials` | **Done** |
| Expansion, step 3 | “What did you receive?” entry point: denial letter (working), bill with EOB and bill with no insurance (honest “coming soon” pages, no upload) | **Done** |
| Expansion, step 4a | Bill check: compare an EOB with a bill line by line; differences worth asking about, each cited; three synthetic sample pairs | **Done** |
| Expansion, step 4b | Uninsured NJ hospital bills: Charity Care bands and the 2008 limit (under 500% of poverty: no more than 115% of Medicare), versioned 2026 poverty guidelines; estimate runs in the browser, income never sent | **Done** |
| Expansion, step 4c | Price context: 16 common services with New Jersey Medicare physician fee schedule amounts (CMS RVU26D, both NJ localities), next to the bill's charge and the hospital's published price; on `/prices` and inside the bill check | **Done** |

Later phases (not being built yet): medical-records access, privacy complaints, policy-document explorer, privacy-preserving analytics.

## Run it locally

Requirements: Node 20+ and Python 3.12 (the same version Vercel runs).

```bash
npm install
```

```bash
python -m venv .venv
```

```bash
.venv/Scripts/python -m pip install -r requirements-dev.txt
```

(On macOS/Linux use `.venv/bin/python`.) Then start the API and the web app in two terminals:

```bash
.venv/Scripts/python -m uvicorn patientshield.app:app --app-dir backend --port 8000 --reload
```

```bash
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to the FastAPI app on port 8000. API docs are at http://localhost:8000/api/docs in
development.

No API keys or secrets are needed. See [`.env.example`](.env.example) for optional settings.

## Test and lint

```bash
.venv/Scripts/python -m pytest
```

```bash
.venv/Scripts/ruff check backend api
```

```bash
.venv/Scripts/python -m pip_audit -r requirements.txt
```

```bash
npm audit
```

```bash
npm test
```

```bash
npm run lint
```

```bash
npm run build
```

Frontend tests include automated accessibility checks with axe.

## Architecture

React + TypeScript (Vite) frontend and a FastAPI backend deployed together on Vercel. Both are split into a shared `core`
(document pipeline, citations, source library, plan-type triage) and one module per workflow under `features/` (today:
`denials`). See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Legal sources and what was or wasn't verified: [docs/SOURCES.md](docs/SOURCES.md).
Security model and review results: [SECURITY.md](SECURITY.md).

## Limitations

- New Jersey and U.S. federal law only. Medicare and Medicaid are routed to their own appeal systems, not fully modeled.
- Deadlines are general rules from official sources. A plan's own documents and letters control.
- Scanned (image-only) PDFs will not be readable until OCR is added.
- Sources are checked by hand on the date shown; laws and agency pages change. Stale or uncertain items are flagged, not hidden.

## Future work

OCR for scanned letters; an optional, server-side AI explanation provider behind an interface, whose quotes must pass the same
citation check as rule-based extraction; Spanish-language support; scheduled link and content checks for the source registry.
