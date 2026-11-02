# Security

PatientShield is a portfolio prototype. It is **not approved for real protected health information** and does not claim HIPAA
compliance. This document records the threat model, the controls in place, and the results of the security review.

## Threat model

| Asset | Threats considered |
| --- | --- |
| Uploaded letters (could contain PHI if misused) | Disclosure via storage, logs, caches, third parties; retention longer than needed |
| The API (public, unauthenticated, serverless) | Resource exhaustion (CPU, memory, function time), malformed or hostile files, injection |
| Users' browsers | XSS from document text or API data, clickjacking, malicious links, third-party tracking |
| Legal accuracy | Fabricated or stale rules presented as fact; document text manipulating results (prompt injection) |

## Controls

- **No storage.** Letters are processed in memory for one request; nothing is written to disk, a database, or logs. Responses are
  `Cache-Control: no-store`. The browser keeps results in memory only (no `localStorage`); "Delete this letter" clears them.
- **Untrusted input.** File type from magic bytes; size (4 MB), page (30), character, time (8 s) and **page-complexity** budgets;
  encrypted PDFs rejected; text-only parsing (no scripts, forms, links or embedded files). Request bodies are capped by
  Content-Length *and* by counting streamed bytes. All request models reject unknown fields and bound every string.
- **No echo.** Error responses never include user input; validation errors mask user-chosen keys.
- **Rendering.** Document text is rendered only as React text nodes (an ESLint rule bans `dangerouslySetInnerHTML`). Every
  citation is re-verified against the page text in the browser; a mismatched response is rejected.
- **Headers.** Strict CSP with no third-party hosts (fonts are self-hosted), `frame-ancestors 'none'`, HSTS, `nosniff`,
  `no-referrer`, `Cross-Origin-Opener-Policy: same-origin`; the API sends `default-src 'none'`. A test fails if the CSP is loosened.
- **Prompt injection.** No LLM is used. Text addressed to software is flagged and quoted, never followed.
- **Legal accuracy.** Every legal statement cites verified sources; a test checks that every number in a statement appears in a
  cited source; uncertain sources are flagged and never presented as fact.
- **Supply chain.** Exact pins for runtime Python dependencies; `pip-audit` and `npm audit --audit-level=high` run in CI on every
  push and pull request to `main`, and a known vulnerability fails the build.

## Review — October 17, 2026

Scope: full codebase (backend, frontend, deployment config), dependency audits, secrets scan of git history, and probes of the
live deployment. All findings were fixed and covered by tests unless noted.

| # | Severity | Finding | Resolution |
| --- | --- | --- | --- |
| 1 | High | A ~10 KB PDF describing a page with 10,000 text operators cost ~30 s of CPU in text extraction (time budget was only checked between pages). | Pre-flight complexity limits per page and per document, counting Form XObject reuse and capping nesting depth. The same file is now rejected in 0.06 s. |
| 2 | Medium | Runtime dependencies `starlette 0.49.3` and `anyio 4.12.1` had 7 published advisories (none exercised by this app's code paths, but shipped to production). | Upgraded to FastAPI 0.143.3, Starlette 1.8.0, anyio 4.15.1; development moved to Python 3.12 to match production. `pip-audit`: no known vulnerabilities. |
| 3 | Medium | Request-size limit relied on `Content-Length`; chunked JSON bodies were unbounded (outside Vercel's own cap). | ASGI middleware also counts streamed bytes and returns 413. |
| 4 | Low | CPU-bound PDF parsing ran inside an async handler, blocking the event loop. | Parsing runs in a worker thread. |
| 5 | Low | Validation errors echoed user-chosen JSON keys (e.g. `<img src=x>`). | Field paths mask anything that isn't a plain identifier. |
| 6 | Low | Triage/plan request strings were unbounded. | Answers and signal codes are constrained to short lowercase tokens. |
| 7 | Privacy | Google Fonts exposed visitors' IP addresses to a third party and required third-party CSP hosts. | Fonts self-hosted; CSP is `'self'` only. Added COOP. |
| 8 | Low (dev only) | `vitest`/`tinypool` advisories in the test toolchain. | Upgraded to vitest 4.1.12. `npm audit`: 0 vulnerabilities. |

No secrets were found in the repository or its history.

## Known limitations and recommendations

- **Rate limiting.** There is no application-level rate limit (an in-process limiter is ineffective on serverless). Recommended:
  a Vercel Firewall rate-limit rule on `/api/extract` and `/api/plan` (for example, 20 requests per minute per IP).
- **Vercel deployment protection** is the team default; production is public by design.
- **No authentication**, by design: there is no account, nothing is stored, and no request depends on another.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository rather than a public issue.
