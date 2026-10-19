# Architecture

## Overview

```
Browser (React + TypeScript, Vite)
  │  same-origin fetch, responses validated with zod
  ▼
/api/*  ──►  Vercel Python function (api/index.py)
               └─ FastAPI app (backend/patientshield/app.py)
                    ├─ core/                       shared by every feature; never imports a feature
                    │   ├─ documents/              parsing (PDF/text, limits), segment, pipeline (per-type registry),
                    │   │                          models (DocumentType, Page, DocumentInfo), pdfgen (synthetic PDFs)
                    │   ├─ citations.py            DocumentCitation (page passage) + SourceCitation (library entry), checks
                    │   ├─ sources/                Source models, verified registry (versioned), lookups
                    │   ├─ claims.py               plain-language legal statements → source ids
                    │   ├─ triage/                 plan-type question tree, classifier, plan profiles
                    │   ├─ dates.py, config.py, security.py
                    │   └─ routes/                 GET /api/health, /api/sources[/{id}], /api/claims,
                    │                              GET /api/triage/flow, POST /api/triage/suggest, POST /api/triage,
                    │                              POST /api/extract (X-Document-Type: denial | eob | bill)
                    └─ features/                   one package per document workflow; features never import each other
                        ├─ denials/                denial-letter fields + signals (registered as the "denial" extractor),
                        │                          synthetic letters, GET /api/samples…, POST /api/plan (action plan)
                        ├─ bill_check/             EOB and bill line items (registered as "eob" and "bill"), matching and
                        │                          flags, synthetic pairs: POST /api/bill-check/compare,
                        │                          GET /api/bill-check/samples, POST /api/bill-check/samples/{id}
                        └─ uninsured/              versioned rules only: GET /api/uninsured/rules (no endpoint accepts income)
```

The frontend mirrors the split: `src/core/` (api clients for http, documents, sources and triage; the layout, document viewer,
triage and source-link components; shared helpers), `src/features/denials/` (Navigator page, field cards, action plan) and
`src/features/bill-check/` (bill check page) and `src/features/uninsured/` (questions, eligibility math, 115% calculator).
`src/pages/` holds the general pages (landing, sources, about). Tests on both sides fail if core imports a feature, or one feature
imports another.

### Adding a document workflow

A feature registers an extractor for its document type with `core.documents.pipeline.register_extractor(doc_type, fn)` and
exposes its routers in `ROUTERS`; `app.py` mounts them. Until a type is registered, uploads of that type get a plain
"coming soon" response (HTTP 422, `not_available`), so a half-built feature cannot be reached by accident. Today `denial`,
`eob` and `bill` are registered.

- **Frontend:** static SPA built by Vite, served by Vercel's CDN. Routes: `/`, `/navigator`, `/bill-check`, `/uninsured`,
  `/sources`, `/about`. The landing page's main action is "What did you receive?" (`core/components/EntryChooser.tsx`), driven by
  `src/core/paths.ts`, the single list of workflows and whether each is `ready`. A path that isn't ready is labelled
  "Coming soon" in the chooser and links to a page that explains what it will and won't do, with no upload control; the backend
  refuses its document type independently (see below).
- **Backend:** one FastAPI app. All routes are under `/api`, and Vercel rewrites `/api/(.*)` to the single Python function.
- **No database.** The source registry is versioned data in code, reviewed through pull requests. Uploaded letters are processed in memory
  within a single request and never written to disk, a database, or logs.

## Data model

| Model | Purpose |
| --- | --- |
| `Source` | One official source: authority, URL (https only), jurisdiction, legal weight (`regulation`, `agency-guidance`, …), dated fields with labels, `last_checked`, verbatim `excerpts`, `verification` (`verified` / `needs-review`) with a required `review_note` when uncertain. |
| `Coverage` | Counts of verified, flagged, binding, federal and NJ sources (shown on the landing page). |
| `ExtractedField` | One detail from the letter (denial reason, appeal instructions, appeal deadline, external review deadline, letter date, insurer, plan, reference numbers): `status` found / not_found, the value(s), a machine-readable `normalized` form where useful, and `citations`. A not-found field carries guidance instead of a guess. |
| `DocumentCitation` | `page`, `start`, `end`, `quote`. Invariant enforced on the server **and** re-checked by the client schema: `pages[page-1].text[start:end] == quote`. |
| `SourceCitation` | `source_id` and an optional excerpt `locator`; checked against the registry, so a statement can only point at a real source and a real excerpt. |
| `DocumentInfo` | Name, `doc_type` (`denial`, `eob`, `bill`), kind (pdf/text), page count, size, and whether it is a synthetic sample. |
| `Signal` | Plan-type clues, urgent-appeal mentions, and text addressed to software (prompt-injection attempts), each cited. Clues are hints for the triage step, never conclusions. |
| `Claim` | One plain-language legal statement and the source ids that support it. Tests check every cited source exists and that every number in the text (180, 72, a phone number, a date) appears in an excerpt, title or citation of a cited source. Claims that cite a needs-review source are flagged in responses. |
| `TriageResult` | Plan type (`nj-regulated`, `marketplace`, `self-funded`, `medicaid`, `medicare`, `other-state`, `government-or-religious`, `unknown`), confidence (`confirmed` / `needs-confirmation`), summary, regulator, cited claims, user-facing uncertainties, how-to-confirm steps, and the answers given. |
| `ActionPlan` | Built from the triage answers, quoted letter facts and the user's situation: computed `deadlines` (each labelled *stated in your letter* or *general rule*, with what it's counted from), `comparisons` (letter quote vs. cited claims, with a neutral note), an ordered checklist whose steps are tagged rule / practical / letter / urgent, documents, questions, contacts, and uncertainties. |

Validation rules enforced by Pydantic at startup (and tested): verified sources need an excerpt; needs-review sources need a note; dates
need a label; URLs must be https; ids are unique.

## Extraction pipeline

1. **core/documents/parsing.py**: decide the file type from its bytes (`%PDF-` magic number), enforce a 4 MB, 30-page, 150k-character and 8-second
   budget, extract text with pypdf (text only; encrypted PDFs rejected), and normalize it (NFKC, strip control and bidi characters).
   The normalized text is what offsets refer to.
2. **core/documents/segment.py**: rebuild passages from line structure, because PDF extraction loses paragraph breaks and wraps sentences. Label lines
   (`Claim Number: …`) and short headings stand alone; a line keeps a paragraph open only if it's near full width (it wrapped).
   Sentences are split with an abbreviation list (`P.O.`, `Dr.`, `a.m.`).
3. **features/denials/fields.py**: fixed regex rules per field. The member's deadline is separated from the insurer's own decision timeline
   ("we will decide within 72 hours"), and external-review deadlines are separated from internal ones.
4. **core/documents/pipeline.py** + **features/denials/extraction.py**: the pipeline parses the file, hands the pages to the
   extractor registered for the document type, and every citation is verified before the result is returned with its warnings
   and retention notice.

Uploads are sent as the raw request body with `X-File-Name` and `X-Document-Type` headers (no multipart parser), read in chunks with a hard cap, and
never written to disk or logged. Sample letters run through the same PDF path, using PDFs generated in memory.

## Bill check (EOB vs. bill)

1. **Reading** (`features/bill_check/lineitems.py`): a service row is a line that starts with a date of service and has at least
   one dollar amount. Amount columns are named from the table header ("Billed Allowed Plan paid You owe"); when the header can't
   be read or a row doesn't line up with it, the row is listed but its amounts are left unlabelled, with a warning. A bill row
   with one amount is its charge. Totals come from labelled lines ("Amount due", "Total you owe") or a "Total" row. Every row
   and total cites its exact line, verified like any other document citation. Money is whole cents.
2. **Comparing** (`compare.py`): bill lines are matched one-to-one with EOB lines. Different dates or different billing codes
   never match; otherwise a match needs a code, the same charge, or a similar description, and the strongest evidence wins.
   The browser sends back values only (dates, codes, short descriptions, amounts), never page text or account numbers.
3. **Flags** are "worth asking about" or "good to know": the bill asks for more than the EOB says you owe, a line repeats, a
   bill line isn't on this EOB, a charge differs, an EOB line was denied, a bill has no service lines. Each cites claims from
   the source library (CMS bill and EOB guides, the HealthCare.gov balance-billing definition, No Surprises Act and NJ
   out-of-network protections) or is marked a practical suggestion. A test fails if any flag uses accusatory words such as
   "overcharge", "error" or "illegal".

## Uninsured New Jersey patients

`GET /api/uninsured/rules` publishes the numbers and cited statements; the browser does the math (`eligibility.ts`), so
household income never leaves the device and there is no endpoint that accepts it (a test checks the route list).

- **Poverty guidelines** are versioned by year (`features/uninsured/rules.py`, 2026: $15,960 for one person plus $5,680 per
  additional person, 48 states and DC, effective January 13, 2026). A test checks every figure against the source excerpts.
- **Charity Care**: at or below 200% of the guideline pays 0%; bands at or below 225/250/275/300% pay 20/40/60/80%; above
  300% the bands end. Full coverage or a hospital outside NJ means it doesn't apply; non-residents are sent to the hospital.
- **The 2008 limit** (P.L.2008, c.60): family gross income *less than* 500% of the poverty level, so exactly 500% is outside
  it; the charge may be no more than 115% of the Medicare rate. The source is flagged for review because the current codified
  text and the Department of Health's sliding scale were not retrieved; the result says so every time.
- Comparisons use integer cents and percents (`income × 100 ≤ line × pct`), so results at a limit follow the rule's wording.
  Statuses are "may be eligible", "check with the hospital", "not based on income" or "doesn't apply"; tests ban promises
  and words like "illegal".

## Plan-type triage

The question tree lives in `core/triage/flow.py` and is served to the UI, which only walks it. Submitted answers are validated against
the tree (no skipped, invented or off-path answers). Clues from the letter (for example "self-funded" or "NJ FamilyCare") are turned
into *suggested* answers that the UI pre-selects with a visible note; the user still confirms every answer, so a plan type is never
inferred silently. "I'm not sure" leads to steps for finding out, never to plan-specific deadlines.

## Action plan

`POST /api/plan` receives the confirmed answers, the quotes the client already holds from its extraction result (page-numbered,
length-capped, extra fields rejected), and a few situation details. No identifiers such as claim or member numbers are sent.
Deadlines are counted from the date the letter says (the notice date, or receipt), falling back to the printed date with a note.
Months clamp to month end; business days skip weekends (holidays are called out, not computed). When the letter and a general rule
disagree, the user is told to plan around the earlier date and ask the plan in writing. The plan never says a rule was broken.
Unknown plan types get letter-stated dates only and start with confirming the plan type. The page prints as a clean handout.

## Source library

`/sources` loads the registry and every claim, so each source shows the statements in PatientShield that cite it (traceability in both
directions). Filters (jurisdiction, legal weight, topic, review status) and search live in the URL, so a filtered view can be shared;
unknown filter values are ignored. A source is marked *due for re-check* 180 days after it was last checked. Every source reference
elsewhere in the app links to `/sources#source-<id>`, which highlights that entry. Those links open in a new tab because the Navigator
holds the letter only in memory. A backend test requires every verified source to be cited by at least one statement.

## Security

See [SECURITY.md](../SECURITY.md) for the threat model and the latest review.


- Uploads and extracted text are untrusted: type checked by magic bytes, size-capped below Vercel's 4.5 MB limit, page,
  time and page-complexity limits (content bytes and text operators per page and per document, Form XObject reuse counted,
  nesting capped) checked before extraction, parsed in a worker thread without executing embedded content, and rendered as text
  only (an ESLint rule bans `dangerouslySetInnerHTML`).
- Request bodies are capped by Content-Length and by counting streamed bytes; request models reject unknown fields and bound
  every string; validation errors mask user-chosen keys.
- Prompt injection: the MVP uses no LLM. Document text is only ever quoted. Any future AI provider must sit behind an interface, run
  server-side, and have every quote verified against the document before display.
- HTTP: strict CSP with no inline scripts and no third-party hosts (fonts are self-hosted), `frame-ancestors 'none'`,
  `nosniff`, `no-referrer`, COOP, HSTS (a test fails if the CSP is loosened); API responses are
  `Cache-Control: no-store` with `default-src 'none'`.
- Errors never echo user input or document text; the catch-all handler logs only the exception type.
- No secrets are required. `.env.example` documents optional settings; nothing sensitive uses a `VITE_*` variable.
- FastAPI's interactive docs are disabled when `PATIENTSHIELD_ENV=production`.

## Testing

- **Backend (pytest):** uninsured rules traced to source text and no income endpoint; bill check (money and column parsing, line-item matching, each flag, sample arithmetic, wording),
  registry validation rules, official-domain URLs, uncertainty flags, API responses, security headers, invalid
  input handling, body-size limit, module boundaries, document-type routing (unbuilt types refused), citation checks.
- **Frontend (Vitest + Testing Library + axe):** poverty-line boundaries just under, at and over 200/300/500%, 115% cap math,
  income never sent; landing content, live coverage, loading/error/retry states, response-schema rejection
  (including non-https links), routing, mobile menu, module boundaries, and automated accessibility checks.

## Deployment

Vercel builds the frontend with `npm run build` and deploys `api/index.py` as a Python function (`.python-version` pins 3.12;
local development uses 3.12 too). The
function bundles `backend/patientshield/**` via `includeFiles` in `vercel.json`.
