# Phase 2: routes and libraries (2026-11-24)

Result: **no code removed**. Every candidate is in real use, or it is a
deliberate fail-closed route that a test asserts. The method and the
evidence are below so the audit can be repeated.

## Routes

Method: every `@router.<verb>("...")` under `backend/app/api/routers/` was
joined with its prefix in `app/main.py`. Each path was then searched in `src/services/api/*.js`,
`agents/mcp/`, and `backend/tests/`.

| Endpoint | Caller | Decision |
|---|---|---|
| `POST /api/account/access-grants` | none in UI/MCP; `tests/test_intelligence_w1_access.py:86` asserts `self_grant_denied` | Keep: fail-closed guard, tested |
| `POST /api/account/billing/provider-events` | none in UI/MCP; `tests/test_intelligence_w1_tenancy.py:42` | Keep: fail-closed (Whop has its own signed route) |
| `GET /api/discovery/jobs/{id}/results.md`, `GET /api/monitors/events.md` | `Accept: text/markdown` path used by `agents/mcp/helix_client.py:38`; documented in `docs/SECURITY_AUDIT.md` | Keep |
| Admin user/org actions, support reply, tags/notes, job cancel/results | `src/services/api/adminService.api.js`, `boardService.api.js`, `discoverService.api.js`, `supportService.api.js` | Keep: used |

The first automated pass reported 24 endpoints with no callers. Most were
false positives: the frontend builds those paths with template strings
(`` `/admin/users/${userId}/ban` ``). They were re-checked one by one.

Pagination: every list endpoint either has a `Query(ge=1, le=100)` bound, or its
service calls `query_bounds.pagination_bounds` (`MAX_PAGE_SIZE`, offset
≤ 1,000,000). Services: admin, analysis, archive, creative, discover,
playbook. The error shape is unchanged (`{"detail": ...}` from `HTTPException`).

## Libraries

| Library | Where it is used | Decision |
|---|---|---|
| `gsap` | `src/components/ui/PillNav.jsx:3`, `CardSwap.jsx:12` | Keep (pill nav and animations must stay) |
| `CardSwap` | `src/features/marketing/LoopsSection.jsx:6` | Keep |
| `ReflectiveCard` | `src/pages/PricingPage.jsx` | Keep |
| `driver.js` | guided tour (1 import in `src/`) | Keep |
| `@sentry/react` | `src/lib/errorReporting.js` (lazy, off without DSN) | Keep |
| `boto3` | `backend/app/services/storage_service.py:131` (R2, lazy import) | Keep. A SigV4 rewrite would need its own test plan |
| `Pillow` | `backend/app/services/avatar_image.py:7` | Keep |
| `python-jose` | JWT in auth | Keep (auth/crypto: no swap without a test plan) |

Verification: no files changed, so build and tests are unaffected. The Phase 1
suite run on local Postgres 16 (704 passed) is the baseline.
