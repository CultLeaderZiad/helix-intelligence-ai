# W6 — Discover proof boundary and W5 follow-up

**Draft, in progress. Do not merge or deploy.** Branch `fix/intelligence-W6` starts at W5 `f7673e9` and targets `fix/intelligence-W5`, never `main`.

## Read-first context

Read README, ARCHITECTURE, API_CONTRACTS, DEVELOPMENT, W5 report and PR #28. `DESIGN_SYSTEM.md` is missing from both W5 and the audit snapshot; existing `src/styles/globals.css` and UI primitives supply the design tokens and accent discipline. The audit is not on W5: its canonical `docs/audit/HELIX-AUDIT.md` was read from fetched `audit/helix-full`, without importing its older application code. Some architecture/API documentation describes historical trial/product behavior; it is not authority to add pricing or checkout.

## A — Discover durable-worker proof: STOPPED (missing non-production key)

Presence-only checks found no configured Discover credentials: `METAPI_API_KEY` (aliases `METAPI_KEY`, `METAPI_TOKEN`), `ADYNTEL_API_KEY`/`ADYNTEL_EMAIL`, `APIFY_API_TOKEN` (alias `APIFY_TOKEN`), `META_ACCESS_TOKEN`, or `BRIGHTDATA_API_KEY`. No authorized non-production key/account was supplied. Per the task's stop condition, Part A is not run; provider success/interruption, durable cancellation cleanup, crash/reclaim and duplicate-delivery proof remain unverified. No fabricated creatives, provider outputs, or replacement browser mocks are used. Provider calls and a durable worker are deliberately not started in the synthetic preview.

## B — Admin-granted access and mutations

Implementation and integrated verification in progress. Preview fixtures contain synthetic identities and workspaces only. No production accounts/data/secrets are used.

## C — Navigation, tour, EN/AR and mobile regression

Managed preview and route/mutation matrix in progress. Final table will distinguish successful checks from blocked or unverified actions.

## D — Weight and warnings

Before build: the largest emitted JS chunk is approximately 508 kB raw and emits Vite's >500 kB warning. Exact raw/gzip comparison and backend warning inventory will be recorded after the route split and warning repairs.

## Verification

In progress. Local PostgreSQL 16 disposable test and preview clusters are separate; the preview API uses a `NOSUPERUSER NOBYPASSRLS` role. All requested gates and final head CI remain pending until recorded here and in the PR handoff.

## Single P0 next step

Supply an authorized **non-production** Discover provider credential through preview secrets, then complete Part A through API → durable outbox/worker → provider, including interruption and immediate terminal work-item cleanup. Do not treat B–D or green static checks as provider proof or production readiness.
