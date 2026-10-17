# Architecture

## Overview

```
Browser (React + TypeScript, Vite)
  │  same-origin fetch, responses validated with zod
  ▼
/api/*  ──►  Vercel Python function (api/index.py)
               └─ FastAPI app (backend/patientshield)
                    ├─ routers/health.py        GET /api/health
                    ├─ routers/sources.py       GET /api/sources, GET /api/sources/{id}
                    ├─ routers/documents.py     POST /api/extract, GET /api/samples,
                    │                           POST /api/samples/{id}/extract, GET /api/samples/{id}/pdf
                    ├─ extraction/              documents → segment → fields → service
                    ├─ samples/                 synthetic letters + in-memory PDF generator
                    ├─ sources/models.py        Pydantic models + validation rules
                    ├─ sources/registry.py      Verified source data (versioned)
                    └─ security.py              Security headers, body-size limit
```

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
| `Citation` | `page`, `start`, `end`, `quote`. Invariant enforced on the server **and** re-checked by the client schema: `pages[page-1].text[start:end] == quote`. |
| `Signal` | Plan-type clues, urgent-appeal mentions, and text addressed to software (prompt-injection attempts), each cited. Clues are hints for the triage step, never conclusions. |
| Planned: `TriageAnswers` → `ResultPlan` | Plan type and dates in; "document says" vs. "rules say," checklist, documents, questions, resources and uncertainties out. Every legal statement cites `Source` ids. |

Validation rules enforced by Pydantic at startup (and tested): verified sources need an excerpt; needs-review sources need a note; dates
need a label; URLs must be https; ids are unique.

## Extraction pipeline

1. **documents.py**: decide the file type from its bytes (`%PDF-` magic number), enforce a 4 MB, 30-page, 150k-character and 8-second
   budget, extract text with pypdf (text only; encrypted PDFs rejected), and normalize it (NFKC, strip control and bidi characters).
   The normalized text is what offsets refer to.
2. **segment.py**: rebuild passages from line structure, because PDF extraction loses paragraph breaks and wraps sentences. Label lines
   (`Claim Number: …`) and short headings stand alone; a line keeps a paragraph open only if it's near full width (it wrapped).
   Sentences are split with an abbreviation list (`P.O.`, `Dr.`, `a.m.`).
3. **fields.py**: fixed regex rules per field. The member's deadline is separated from the insurer's own decision timeline
   ("we will decide within 72 hours"), and external-review deadlines are separated from internal ones.
4. **service.py**: verifies every citation before returning, adds warnings, and states the retention behavior.

Uploads are sent as the raw request body with an `X-File-Name` header (no multipart parser), read in chunks with a hard cap, and
never written to disk or logged. Sample letters run through the same PDF path, using PDFs generated in memory.

## Security

- Uploads and extracted text are untrusted: type checked by magic bytes, size-capped below Vercel's 4.5 MB limit, page
  and time limits, parsed without executing embedded content, rendered as text only (an ESLint rule bans `dangerouslySetInnerHTML`).
- Prompt injection: the MVP uses no LLM. Document text is only ever quoted. Any future AI provider must sit behind an interface, run
  server-side, and have every quote verified against the document before display.
- HTTP: strict CSP with no inline scripts, `frame-ancestors 'none'`, `nosniff`, `no-referrer`, HSTS; API responses are
  `Cache-Control: no-store` with `default-src 'none'`.
- Errors never echo user input or document text; the catch-all handler logs only the exception type.
- No secrets are required. `.env.example` documents optional settings; nothing sensitive uses a `VITE_*` variable.
- FastAPI's interactive docs are disabled when `PATIENTSHIELD_ENV=production`.

## Testing

- **Backend (pytest):** registry validation rules, official-domain URLs, uncertainty flags, API responses, security headers, invalid
  input handling, body-size limit.
- **Frontend (Vitest + Testing Library + axe):** landing content, live coverage, loading/error/retry states, response-schema rejection
  (including non-https links), routing, mobile menu, and automated accessibility checks.

## Deployment

Vercel builds the frontend with `npm run build` and deploys `api/index.py` as a Python function (`.python-version` pins 3.12). The
function bundles `backend/patientshield/**` via `includeFiles` in `vercel.json`.
