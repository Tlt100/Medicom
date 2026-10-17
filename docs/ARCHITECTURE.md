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
                    ├─ sources/models.py        Pydantic models + validation rules
                    ├─ sources/registry.py      Verified source data (versioned)
                    └─ security.py              Security headers, body-size limit
```

- **Frontend:** static SPA built by Vite, served by Vercel's CDN. Routes: `/`, `/navigator`, `/sources`, `/about`.
- **Backend:** one FastAPI app. All routes are under `/api`, and Vercel rewrites `/api/(.*)` to the single Python function.
- **No database.** The source registry is versioned data in code, reviewed through pull requests. Uploaded letters (milestone 2) will be
  processed in memory within a single request and never written to disk, a database, or logs.

## Data model

| Model | Purpose |
| --- | --- |
| `Source` | One official source: authority, URL (https only), jurisdiction, legal weight (`regulation`, `agency-guidance`, …), dated fields with labels, `last_checked`, verbatim `excerpts`, `verification` (`verified` / `needs-review`) with a required `review_note` when uncertain. |
| `Coverage` | Counts of verified, flagged, binding, federal and NJ sources (shown on the landing page). |
| Planned: `ExtractedField` | A field from the letter (denial reason, appeal instructions, deadline, plan/insurer, reference number) with the exact quote and page, or an explicit "not found." |
| Planned: `TriageAnswers` → `ResultPlan` | Plan type and dates in; "document says" vs. "rules say," checklist, documents, questions, resources and uncertainties out. Every legal statement cites `Source` ids. |

Validation rules enforced by Pydantic at startup (and tested): verified sources need an excerpt; needs-review sources need a note; dates
need a label; URLs must be https; ids are unique.

## Security

- Uploads and extracted text are untrusted (milestone 2): type checked by magic bytes, size-capped below Vercel's 4.5 MB limit, page
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
