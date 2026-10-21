# W5 — Discover reliability and focused product

Draft PR #28: `fix/intelligence-W5` → `fix/intelligence-W4`. W4 PR #26 remains draft and is not retargeted. Reference audit: `audit/helix-full` (`a7d5628`); W5 starts from W4 `eab70cc`.

No merge, force-push, manual deployment, production database/account access, purchasable pricing, or billing feature was performed/added. Browser data is limited to synthetic local accounts and real local API job states; no fabricated provider results were displayed. This is **not production readiness**.

## A. Discover reliability

- Tenant-validated cancellation, durable cancelled/timed-out terminal states, absolute job deadlines, bounded provider calls, heartbeat/lease renewal and reclaim, and generation/owner fencing of completion and result writes. The deadline migration includes the matching ORM index.
- UI uses server stage labels rather than a fixed animation. Polling is sequential, deduplicated, backed off, stopped at terminal states and paused in a hidden tab. Cancellation and terminal retries are explicit in EN/AR; a lost cancellation acknowledgement is not shown as confirmed cancellation.
- Six PostgreSQL reliability tests cover mid-provider cancellation and cross-tenant denial, running/queued deadline expiry, provider timeout distinct from job deadline, crash/reclaim with stale-completion fencing and duplicate delivery, and live heartbeat renewal. These use test providers, not claimed vendor success.

## B. Narrow product and access

- Discover is the primary loop. Unbuilt/experimental loops, Billing & Meter, API-key/team surfaces and unsupported admin tools are hidden behind the existing explicit experimental flag. Direct hidden routes redirect rather than expose a mock product.
- Access & Usage reads actual admin-grant state; approved and pending users see different server-reported states. There is no checkout or plan-purchase flow. Internal usage is disclosed as usage, not payment credits.
- Legal/footer and localStorage disclosures no longer claim proven encryption, legal approval or complete deletion. Documentation landing copy removes trial/refund/purchase promises, and marks technical articles as potentially historical/experimental reference.
- The admin health page was observed presenting unwitnessed provider-readiness claims; its navigation and direct route are now experimental-only, not a default product health guarantee.

## C. Onboarding and tour

- Honest two-step setup without “Zero Cost”; industry selection prefills an editable query and is explicitly not a saved profile preference. Clearing the query does not run a search. Setup uses repository theme tokens.
- Only visible Discover targets enter the tour: three desktop steps, two mobile steps (hidden desktop navigation omitted). EN/AR direction, focus, Escape/close, body-scroll cleanup and server-side completion/dismissal are handled. Settings and Help can restart a persisted tour; the mobile Help action closes its drawer.

## D. Navigation and localization

- API proxy matches `/api` path boundaries without swallowing `/api-keys`; Vercel SPA fallback and asset exceptions are covered. Hidden `/api-keys` and `/admin/health` directly loaded back into Discover in the preview.
- Route focus/back/forward and mobile drawer behavior were checked. Auth, support, notifications, profile settings, docs chrome and Discover copy have scoped EN/AR improvements. Technical Markdown remains English, disclosed on the AR docs surface.

## E. Diagnostics and test corrections

- No blanket ignores, gate filtering, typecheck scope exclusions or skipped failing tests were added.
- The migration proof follows the actual Alembic head, and the provider-outage test expects a sanitized failure rather than leaked vendor text.
- Final verification exposed two test-harness defects: a 200 ms deadline could elapse before the mock provider entered; the test now requires entry and cancellation within a bounded five-second deadline. The RLS worker-claim assertion now targets its own queued fixture instead of an unrelated row left by another test. The provider-stop, tenancy and RLS assertions remain intact.

## Verification — final integrated source

All database writes below used a separate disposable local PostgreSQL 16 database, not the preview/app database or production. The temporary verification database/login were removed afterward. An initial run against a restricted application role failed fixture inserts under RLS; it is **not** the final result and was not repaired by weakening application RLS.

| Command | Exit | Final result |
|---|---:|---|
| `cd backend && python -m pytest -q tests` | 0 | **234 passed**, 18 warnings; [log](evidence/backend-tests.log) |
| `cd backend && python -m pytest -q tests/test_intelligence_w5_discovery_reliability.py` | 0 | **6 passed**; [log](evidence/discover-reliability.log) |
| `cd backend && python -m compileall -q app` | 0 | [log](evidence/compileall.log) |
| `alembic upgrade head` | 0 | Fresh isolated database to `d1f9c4a7b263` |
| `alembic check` | 0 | No new upgrade operations |
| `alembic downgrade -1` | 0 | Isolated rollback database only |
| `alembic upgrade head` then `alembic check` | 0 / 0 | Restored head without drift; [whole cycle](evidence/migration-cycle.log) |
| `pnpm test` | 0 | **5 Node + 146 Vitest tests**, 26 Vitest files; [log](evidence/frontend-tests.log) |
| `pnpm build` | 0 | [log](evidence/frontend-build.log); >500 kB chunk warning remains |
| `pnpm typecheck` | 2 | **483 → 170 diagnostics**, zero in W5-touched source files |
| `pnpm lint` | 1 | **159 → 118 errors**, zero warnings and zero in W5-touched source files |
| `cd backend && python -m pyflakes app` | 1 | **127 → 124 diagnostics**, zero in changed app files |
| `git diff --check` | 0 | No whitespace errors |

Full remaining file/line diagnostics are in [diagnostics-after.txt](diagnostics-after.txt). The typecheck remainder includes 16 dependency-source diagnostics in `punycode`; these were not present in the original baseline and are **not** described as inherited source errors. The current comparison includes 82 changed/new frontend source files. Generated `dist/index.html` and docs Git metadata were restored after builds. See [files-changed.txt](files-changed.txt) for the full W5 file set.

### Fresh managed-preview checks

Managed preview: `agent-preview:3000/`; real local API on port 8000, local disposable preview database. `/health` returned HTTP 200. The final managed HTTP probe returned 200; its automatic headless probe timed out, so interactive evidence below, not that probe alone, supports the UI results.

- **Discover EN/AR:** actual server job submission, queued cancellation, server-confirmed cancelled state, terminal retry and server deadline expiry. An AR terminal job was also fetched from the API: HTTP 200, `status=timed_out`, `failure_kind=deadline`. No successful provider scrape/result set was obtained. Browser cancellation did not prove mid-provider interruption; the PostgreSQL test covers that separately.
- **Onboarding/tour:** EN/AR at 1280×800 and 390×844; both setup steps; three desktop/two mobile tour steps; complete/dismiss, reload persistence, Settings restart, keyboard focus trap, Escape and scroll/overlay cleanup. After the industry fix, the AR query field contained the selected Arabic industry; the recorded EN flow contained “Software & apps”, permitted clearing it, and completed all tour steps. No horizontal overflow was observed in these checked states.
- **Member routes:** Discover, Access & Usage, Docs, Support, Settings and Notifications directly loaded in EN/AR. Back/forward restored the route and focused `main-content`. Docs search opened and closed; notifications/support empty states resolved. Pending access displayed an admin request form, not a plan-purchase banner.
- **Admin routes:** overview, organizations, access requests, users, support, updates and audit log opened in EN/AR; navigation was translated and layout used RTL, but much existing admin body copy remains English. Direct `/admin/health` redirected after being hidden. Administrative mutations were not executed.
- **Recording:** local fixture login, editable industry search, full EN desktop tour, confirmed cancellation and retry-to-timeout were checked during recording. No uncaught browser errors were returned for the recorded flow. Only masked test credentials and synthetic identities are visible.

Screenshots and before/after captions: [screens/README.md](screens/README.md). [Walkthrough recording](https://dlzlyg5a5kv7c.cloudfront.net/ef5afe12cb4f4d1f9c8f1f8e91dcb783fe5e8505a4c74d9fa6baf89d269f9660.webm) (external evidence link expires after seven days; no authentication-state file is committed).

## Remaining broken items and unverified work

**Observed remaining issues**

1. Repository-wide typecheck, lint and pyflakes still fail at the counts above; changed source/app files are clean, but this is not a green repository gate.
2. Existing administrative org/user pages still expose trial/plan template terminology and English body copy in AR. The Users table rendered `Invalid Date` for local fixture timestamps. These are not presented as fixed.
3. Technical Markdown article bodies and some search-result titles remain English. Docs chrome/landing is localized and discloses this limit.
4. Build chunk-size and backend deprecation/runtime warnings remain; no performance or warning-free claim is made.

**Not verified**

- Real, authenticated non-production provider success and a complete result-selection flow. Browser runs verified queued cancellation/deadline states, not live vendor interruption. Lease fencing proves durable completion/result idempotency, not vendor-side at-most-once execution under a lost lease.
- Cancellation through the durable work-outbox worker's `CancelledError` branch and immediate terminal **work-item** cleanup. Code inspection suggests it may remain running until lease cleanup even though the API job is terminal; the direct cancellation test does not exercise that path. No claim of complete worker-cancellation proof is made.
- Every mutating admin control (approve/revoke, role/credit edits, impersonation effects, publishing updates, support replies), avatar upload, profile/password writes, reset-email delivery, and browser-injected region-error/RTL fallback. Opening a route is not proof of each action.
- Production deployment/DB/RLS/provider configuration, approved legal/privacy contacts, end-to-end erasure, production processors, encryption guarantees, or live external error-reporting delivery. They were not accessed or represented as complete.
- Final GitHub CI/review state is reported in the PR comment; local passes do not imply CI passes or approval.

## Single P0 next step

**Prove the full Discover success/cancel/timeout flow through the durable worker with an authorized non-production provider, including provider interruption and terminal work-item cleanup.** Keep this PR draft; do not merge or deploy on the strength of the local checks alone.
