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
                        └─ denials/                denial-letter fields + signals (registered as the "denial" extractor),
                                                   synthetic letters, GET /api/samples…, POST /api/plan (action plan)
```

The frontend mirrors the split: `src/core/` (api clients for http, documents, sources and triage; the layout, document viewer,
triage and source-link components; shared helpers) and `src/features/denials/` (Navigator page, field cards, action plan).
`src/pages/` holds the general pages (landing, sources, about). Tests on both sides fail if core imports a feature, or one feature
imports another.

### Adding a document workflow

A feature registers an extractor for its document type with `core.documents.pipeline.register_extractor(doc_type, fn)` and
exposes its routers in `ROUTERS`; `app.py` mounts them. Until a type is registered, uploads of that type get a plain
"coming soon" response (HTTP 422, `not_available`), so a half-built feature cannot be reached by accident. Today only
`denial` is registered; `eob` and `bill` are reserved for the bill-check and uninsured modules.

- **Frontend:** static SPA built by Vite, served by Vercel's CDN. Routes: `/`, `/navigator`, `/sources`, `/about`.
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

- **Backend (pytest):** registry validation rules, official-domain URLs, uncertainty flags, API responses, security headers, invalid
  input handling, body-size limit, module boundaries, document-type routing (unbuilt types refused), citation checks.
- **Frontend (Vitest + Testing Library + axe):** landing content, live coverage, loading/error/retry states, response-schema rejection
  (including non-https links), routing, mobile menu, module boundaries, and automated accessibility checks.

## Deployment

Vercel builds the frontend with `npm run build` and deploys `api/index.py` as a Python function (`.python-version` pins 3.12;
local development uses 3.12 too). The
function bundles `backend/patientshield/**` via `includeFiles` in `vercel.json`.
