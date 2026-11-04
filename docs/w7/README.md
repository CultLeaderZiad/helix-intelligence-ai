# W7 — leftovers, full-stack review and managed preview

**In progress. Draft PR into `fix/intelligence-W6`; do not merge or deploy.** W7 starts at W6 `a1e2d68`. No production-readiness claim. The audit source is `audit/helix-full:docs/audit/HELIX-AUDIT.md`, absent from W6's working tree.

## A — W6 leftovers

The managed preview now uses a new loopback PostgreSQL database, without W6's seeded identities or data. Users are registered through the real application. Initial local administrator bootstrap is environment setup, not proof of an administrator mutation. Optional external providers, email and storage integrations are disabled. Preview port configuration now uses the supported schema; startup initializes/migrates the local database idempotently.

Production-origin safeguards, repeated-read classification and fixes, and remaining admin interaction coverage are being reviewed. Final evidence and limitations will replace this checkpoint before handoff.

## B — durable-worker Discover: BLOCKED / STOPPED

Presence-only checks found no authorized non-production ad-provider credentials: `METAPI_API_KEY` (or supported aliases), `ADYNTEL_API_KEY` plus `ADYNTEL_EMAIL`, `META_ACCESS_TOKEN`, or `APIFY_API_TOKEN` (alias `APIFY_TOKEN`). No provider calls or worker-based provider success are claimed. The complete provider/base-URL/worker inventory is the first W7 PR comment.

Success/persisted real results, queued/running cancellation, deadline cleanup, provider interruption, killed-worker reclaim/fencing and duplicate-delivery proof are all unverified. Controlled regression tests do not close this gap.

## C — full-stack review

Review and fixes are in progress across security/auth/tenancy/RLS, configuration, workers/outbox/providers, migrations/rollback, API contracts, admin/member UX, accessibility, EN/AR/RTL and performance. The final findings table and human-only merge-readiness checklist will be added after independent findings are reconciled.

## D — live preview

Managed Preview is running a fresh, isolated database. Signup produced a real local account and workspace while creatives remained empty. Final-head EN/AR desktop/mobile route, action, console/network, persistence and walkthrough evidence is pending. No W6 screenshots or prior test results count as W7 evidence.

## Gates and remaining work

Final-head backend/static/migration/frontend gates and CI have not yet been run. Nothing is claimed complete from this checkpoint. No production database, provider account or production API/media origin is used by the local verification. No merge, auto-merge or manual deployment is permitted.

**Single P0:** obtain an authorized non-production ad-provider key and prove the complete durable-worker path with real persisted results and the requested cleanup/fencing/recovery cases.
