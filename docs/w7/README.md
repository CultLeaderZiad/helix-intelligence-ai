# W7 — security fixes, W6 leftovers and preview evidence

**Reviewable, not merge-ready.** [Draft PR #30](https://github.com/CultLeaderZiad/helix-intelligence-ai/pull/30) targets `fix/intelligence-W6` (`a1e2d68149608a0b10266d7559aa439e0281abdc`). Application implementation: `6d3f3ba912c7780a7685c1c54aaf8bfc98684933`; subsequent handoff changes contain documentation/evidence only. Auto-merge is disabled. No merge or manual deployment was performed, and no production-readiness claim is made.

The outstanding **P0 acceptance blocker is real-provider durable-worker proof**. No authorized non-production provider credentials were available, so Part B remains stopped. Passing regressions and an empty Discover screen are not provider success.

## Scope and review sources

W7 closes the evidenced W6 configuration, repeated-read and security gaps without adding billing, pricing or checkout. Access remains administrator-granted. Review used `README.md`, `ARCHITECTURE.md`, `API_CONTRACTS.md`, `DEVELOPMENT.md`, the W5/W6 reports, and PRs #26, #28 and #29, including their diffs and discussion. The audit source is `audit/helix-full:docs/audit/HELIX-AUDIT.md`; it is absent from the W6 working tree. Earlier-wave findings and screenshots are reference material, not new W7 proof.

The managed preview uses a fresh, disposable loopback PostgreSQL database and a restricted application role (`NOSUPERUSER`, `NOBYPASSRLS`), not Neon or a production database. Accounts were registered through the application. Promoting the initial local operator is environment bootstrap, not evidence of an administrator mutation. No provider results, creatives or usage were seeded. Optional provider, remote storage and email integrations are disabled; `USE_MOCKS=false`.

## A/C — findings, impact and disposition

References below are to implementation `6d3f3ba`. Severity describes the reviewed risk, not a claim that exploitation occurred.

| Severity | Finding / impact | Fix and evidence | Disposition |
| --- | --- | --- | --- |
| P0 acceptance gate | Real-provider and durable-worker outcomes are unproved. A UI render or controlled provider regression cannot establish real delivery, persistence or recovery. | Provider inventory and exact missing prerequisites are in [the W7 blocker comment](https://github.com/CultLeaderZiad/helix-intelligence-ai/pull/30#issuecomment-6625302193). | **Blocked; Part B stopped.** |
| P1 | Environment/origin ambiguity could send preview traffic outside loopback or accept HTTPS IP/private/reserved targets in production. Vite production mode could be treated as development when the app environment was unclassified. | Fail-closed environment/origin handling in `backend/app/core/origins.py:60-132`, `backend/app/core/config.py`, `src/services/origin.js:31-65`, `src/services/config.js`; regressions in `backend/tests/test_config_origins.py` and `src/services/__tests__/origin-config.w7.test.js`. Explicit production API/media origins are required. | Fixed and regression-tested. DNS/TLS/operator configuration still needs human verification. |
| P1 | Notification responses or completed cached reads could cross an unresolved user/session/organization transition. | Session-scoped cache, generation checks, auth-transition guards and mutation invalidation in `src/hooks/notificationReadCache.js:22-98`, `src/hooks/useNotifications.js`, `src/components/NotificationBell.jsx`, `src/pages/NotificationsPage.jsx`. Tests: `src/hooks/__tests__/member-flows.w6.test.jsx:182-254` and `src/components/__tests__/NotificationBell.w6.test.jsx`. | Fixed. Completed reads are reused for 10 seconds; independent in-flight requests retain their own cancellation lifecycle. |
| P1 | A removed member's API key could outlive membership. | Membership is rechecked during authentication and affected keys are deactivated on removal: `backend/app/services/api_key_service.py:90-126`, `backend/app/services/team_service.py:291-303`. Tests: `backend/tests/test_w7_security_regressions.py:38-128`. | Fixed and regression-tested. |
| P1 | Temporary tenant scope for invitation/scoped operations could be absent or leak into following work. | Scoped binding/restoration in `backend/app/core/tenancy.py:169-194` and `backend/app/services/team_service.py`. Tests verify scope application/restoration: `backend/tests/test_w7_security_regressions.py:130-185`. | Fixed; RLS was not relaxed. |
| P1 | Role demotion could leave platform-admin capability behind; privileged users could be impersonation targets. | Synchronize platform-admin status and reject privileged impersonation targets in `backend/app/services/admin_service.py:763,863-917`, `backend/app/api/routers/admin.py:182`. Tests: `backend/tests/test_w7_security_regressions.py:186-222`. | Fixed and regression-tested. |
| P1 | Avatar/media references and signed-upload checks needed owner, membership and token-version scoping. | Owner-specific avatar validation in `backend/app/api/routers/account.py`, storage URL/capability checks in `backend/app/services/storage_service.py:183-274,395`, tenant-scoped signed-upload checks in `backend/app/api/routers/uploads.py:118-124`, bounded image handling in `backend/app/services/avatar_image.py`. Tests: `backend/tests/test_avatar_local_storage.py`, `backend/tests/test_w7_security_regressions.py:248`. | Fixed locally. Remote object-storage durability is not established. |
| P1 | Unbounded support context and credential-like nested fields could persist sensitive material, including `auth`/`authentication` values. | Ticket field/context bounds (JSON-serializable, at most 16 KB) in `backend/app/api/routers/support.py:18-30`; nested redaction in `backend/app/services/support_service.py`. Tests: `backend/tests/test_w7_security_regressions.py:223-247`. | Fixed and regression-tested. |
| P1 safety / verification | A destructive migration-proof helper could fall back to an application database; skipped database tests weakened acceptance evidence. | Explicit disposable, loopback PostgreSQL proof target required in `backend/scripts/prove_prod_schema_reconcile.py`; failure/stamp/retry regression in `backend/tests/test_migration_failure.py:23-46`; CI executes database, rollback and zero-skip gates in `.github/workflows/ci.yml`. | Fixed; local rollback cycle and CI pass. No production database was touched. |
| P2 reliability | W6 reported repeated notification/update reads. Preview startup could also remove PostgreSQL directory traversal permission. | Completed-read caching/invalidation as above; supported ports, isolated initialization/migration and permission preservation in `.hoplite/settings.json` and `.hoplite/scripts/{preview-common,setup-local,run-local}.sh`. | Route evidence records no duplicate reads. The local permission failure was repaired and backend gates rerun successfully. |
| P2 copy | Preview copy mislabeled local PostgreSQL as Neon, described access as billing, and used an unrelated provider name on the Updates card preview. | Default-route copy corrected in `src/pages/admin/DataSourcesPage.jsx`, `src/i18n/adminMessages.js`, `src/i18n/w5Support.js`, `src/pages/admin/UpdatesPage.jsx`. | Corrected on the default W7 surface; optional legacy health-page limitation below. |

### Remaining lower-priority limitations

- **Production DNS is not resolved by configuration validation.** A syntactically valid dotted hostname (including a reserved `.invalid` fixture) can pass. The guard rejects unsafe literal/loopback targets; it does not prove public DNS resolution, certificate validity, or correct deployment configuration.
- **Concurrent requests are not globally coalesced.** The notification cache intentionally keeps independently abortable in-flight reads separate. The recorded route matrix contains no duplicate reads, not a universal guarantee that every concurrent interaction issues one request.
- **Optional legacy health copy:** `src/pages/admin/SystemHealthPage.jsx:85-88` still assumes Neon/PgBouncer/multi-region hosting. `/admin/health` is behind `optionalPage` / `EXPERIMENTAL_FEATURES_ENABLED` (`src/App.jsx:220`) and is outside the default W7 visible-route matrix. Correct this before enabling that surface.
- **Updates form accessibility:** title/body still rely on placeholders and some visible select labels lack `htmlFor`/`id` association (`src/pages/admin/UpdatesPage.jsx:547-579,658-665`). Deferred P2; route rendering and empty-form validation do not close this accessibility gap.

## B — real-provider proof: blocked / stopped

Presence-only inventory found no authorized non-production credentials for `METAPI_API_KEY` (or supported aliases), `ADYNTEL_API_KEY` plus `ADYNTEL_EMAIL`, `META_ACCESS_TOKEN`, or `APIFY_API_TOKEN` / `APIFY_TOKEN`. No production key, account, origin or database was substituted. No live-provider request or worker success is claimed, and mocks were not used as live proof.

The following remain **unverified**: genuine provider results persisted and visible after reload; queued/running cancellation; deadline cleanup; provider interruption; worker termination and reclaim; fencing of stale work; duplicate-delivery handling. Controlled backend regressions cover relevant code but do not satisfy this live acceptance gate. Resume only after an authorized non-production provider/account and its base URL are supplied, keeping the durable worker/outbox path and security gates intact.

## D — managed preview and browser evidence

Preview handoff: **`agent-preview:3000/`**. An automated browser probe initially exceeded its deadline while HTTP remained 200. Direct browser checks succeeded; a later managed `preview_start` returned **ready**, HTTP 200, zero reported console errors and zero uncaught exceptions, without changing production configuration.

### Recorded route matrix

| Group | Routes × language/viewport combinations | Passed | Evidence |
| --- | --- | --- | --- |
| Public | 30 route cases (28 unique paths) × EN/AR × 1280×800 / 390×844 | 120/120 | [routes-public.json](evidence/routes-public.json) |
| Admin | 7 × EN/AR × 1280×800 / 390×844 | 28/28 | [routes-admin.json](evidence/routes-admin.json) |
| Member | 5 × EN/AR × 1280×800 / 390×844 | 20/20 | [routes-member.json](evidence/routes-member.json) |

These **168 recorded states** check expected routing/direction, horizontal overflow, unexpected dialogs, invalid dates, error boundaries, failed/duplicate API reads and browser errors. None was recorded in the passing matrix. Public/admin sweeps ran on the W7 working candidate before the implementation commit; the member sweep ran after `6d3f3ba`. Do not describe every matrix state as an immutable post-commit rerun. This is route/state coverage, not proof of every control, negative authorization path or provider-dependent state.

### Interactions and honest limits

- **Signup:** the first helper used reserved `example.test`, received HTTP 422 and timed out; it is not a successful signup. A corrected `example.com` signup returned HTTP 200 and reached onboarding. Local schema validation independently confirms the reserved-domain rejection. The final recording signs into that real local account; it does not present the failed attempt as success.
- **Onboarding:** industry selection prefills the optional query; the query was cleared before completing setup to avoid any provider submission. Completion persisted after reload. [Onboarding screenshot](screens/onboarding-en-1280.png).
- **Tours/history/mobile:** settings/sidebar restart, skip/close and finish persistence, one active tour, browser back/forward, AR mobile layout and drawer Escape cleanup are recorded in [tour-history.json](evidence/tour-history.json). The fresh implementation-head walkthrough also verifies restart, step progression, completion, reload persistence and EN→AR support navigation: [walkthrough.json](evidence/walkthrough.json).
- **Admin:** preliminary W7 UI observations recorded actual access request → administrator approval → member reload, and support submission. Final route evidence renders the resulting local state. Empty-title validation was exercised. [admin-failure.json](evidence/admin-failure.json) records a deliberately aborted Updates read showing an error, followed by recovery after removing interception; this is error-state testing, not a fabricated provider response.
- **Coverage limit:** the fresh recording opens settings but does not repeat profile/avatar/password mutations or every admin mutation/403 path. Earlier manual observations and regression tests must not be represented as a fresh, exhaustive four-configuration action matrix. External email delivery, remote storage durability, provider-dependent features and experimental/hidden routes remain outside this proof.

### Media

- [Silent 69.8-second desktop EN/AR walkthrough](evidence/walkthrough.webm): sign-in, tour restart/finish, reload persistence, admin-granted access, settings and support. It contains synthetic local identities and no provider results. The WebM decoded successfully; representative frames at 2/15/30/45/67 seconds were inspected for progress and the ending.
- [Fresh AR mobile support](screens/walkthrough-support-ar-390.png) and [AR desktop support](screens/walkthrough-support-ar-1280.png). Mobile interaction checks are separate from the desktop recording because the recorder does not permit changing viewport dimensions during capture. Failed/incomplete recording attempts are not published as successful evidence.
- Additional inspected screenshots are in [screens/](screens/), including admin access/users/organizations, Discover, docs, settings and support in EN/AR desktop/mobile states. There are 21 screenshots; they do not imply every state has a screenshot.

## Verification gates

[verification.json](evidence/verification.json) retains a sanitized summary. Full local logs remain under `/tmp/w7-final-gates/` and are not committed with environment or credential material.

| Gate | Result |
| --- | --- |
| `python -m compileall -q backend/app` | Exit 0 |
| `python -m pyflakes backend/app` | Exit 0 |
| Full backend pytest suite, PostgreSQL-backed, zero-skip enforcement | **276 passed, 0 skipped**, exit 0 |
| Isolated migration cycle | Upgrade → `alembic check` → downgrade `-1` → re-upgrade → `alembic check`: all exit 0; both checks report no new upgrade operations |
| `pnpm typecheck` / `pnpm lint` | Both exit 0 |
| `pnpm test` | **37 files, 202 tests passed**, exit 0 |
| `pnpm build` | Exit 0 |
| Implementation CI | [Run 41819918774](https://github.com/CultLeaderZiad/helix-intelligence-ai/actions/runs/41819918774), exact head `6d3f3ba`: all CI jobs successful |
| Browser/media | 168 recorded route states; fresh implementation-head walkthrough passed with no recorded failed requests, console errors, uncaught errors or Discover submissions; video decode exit 0 |

Local gate logs predate the commit object; they are candidate-source evidence, supplemented by exact-head CI. The migration cycle ended before the final origin/cache/permission edits; W7 changes no migration or model files, and exact-head CI also runs the migration/rollback gate. No skips were introduced to hide failures. Earlier failures were repaired (preview directory permissions and deterministic/auth/database test setup) and the complete backend/frontend gates were rerun. The documentation/evidence-only handoff head must still have its own checks inspected before any readiness decision.

## Human-only merge-readiness checklist — Ziad

**Not authorization to merge or deploy.** The agent leaves PR #30 draft and auto-merge off. All production-side decisions/actions belong to Ziad.

- [ ] Resolve the P0 provider prerequisite using authorized non-production credentials, then collect the complete durable-worker success/persistence/cancel/deadline/interruption/reclaim/fencing/duplicate-delivery evidence.
- [ ] Review the security changes and remaining P2/coverage limitations above; explicitly accept or schedule them. Recheck unproved admin/profile mutations and authorization failures where acceptance requires them.
- [ ] Inspect the latest remote head, draft/base settings, every required check, review feedback and unresolved threads. Green CI without human review is not approval; CodeRabbit skipping a draft is not a review score.
- [ ] Review the stack in order: **#19 → #20 → #21 → #25 → #26 → #28 → #29 → #30**. Verify each base/ancestry; reassess descendants after parent merges. Do not bypass branch protection or merge the entire stack blindly.
- [ ] Separately verify intended production DNS/TLS/origins, secret/account ownership, database roles/RLS, backup/restore and migration/rollback procedures. Any production schema, role/GRANT, Render `DATABASE_URL` or environment change is **Ziad-only**, outside this run.
- [ ] Only after evidence, reviews and required checks are accepted, decide whether to remove draft status and merge/deploy through the normal human-controlled process. This report does not recommend doing so while Part B is blocked.

No pushes to `main`, merges, auto-merge enablement, manual deployments, production database changes, GRANTs, Render `DATABASE_URL` changes or production environment changes were performed. Provider-side deployment comments/statuses are reported as external checks, not as an agent-initiated deployment. `.hoplite/attachments/`, local credentials, raw browser state and failed recordings remain unstaged.
