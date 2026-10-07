# Helix Intelligence — complete production-readiness remediation

## Your assignment

You are the implementation owner for Helix Intelligence. Apply and verify the attached production-readiness audit across the entire active codebase. This is an implementation task: inspect, reproduce, change code, migrate schemas safely, write meaningful regression tests, run them, and deliver a reviewable implementation.

The audit contains **82 findings: 12 P0, 49 P1, 19 P2, 2 P3**, identified as **F01–F82**. Address every ID. The audit's original PR intentionally compared the complete repository against an empty branch and will never be merged. Work from the current active implementation branch; do not merge that audit PR or treat its all-new diff as an ordinary feature patch.

Repository: `CultLeaderZiad/helix-intelligence-ai`.
Audited commit: `fa8164920031a8dfaa036e2a67ee6f107a48a9f2`.
Stack: FastAPI, SQLAlchemy, Alembic, Neon PostgreSQL, React/Vite on Vercel, Scrapling worker, Cloudflare R2, credit-metered jobs and third-party search/ads/LLM providers.

Critical incident: adding `users.signup_metadata` without an Alembic migration broke ORM reads, sign-in, LOOP and WORKSPACE while health stayed green. Prevent this class of failure across **every model and deployment path**, not just this column.

## 1. Required inputs and evidence discipline

Read these supplied files before implementation:

1. `helix-audit/audit-summary.md`: complete A–G audit, failures, fixes, limitations and priorities.
2. `helix-audit/findings.json`: canonical 82-ID worklist, severity, source references, reproductions and suggested fixes.
3. `helix-audit/schema-appendix.md`, `schema-mismatches.json`, `schema-inventory.json`: complete schema comparison.
4. `helix-audit/route-matrix.md`, `routes.json`: every route, aliases, public exceptions and auth boundaries.
5. `helix-audit/inline-comments.md` or `inline-comments.json`: exact-line review context.
6. `helix-audit/validation-evidence.json`, `reproduction-results.json`, `probes/`: prior checks and focused reproductions.
7. `helix-audit/code-health.md`, `frontend-state-inventory.json`, `file-coverage.json`: remaining coverage and code-health inventory.

Audit paths/line numbers refer to the audited revision and an old sandbox. Locate equivalent current code. Compare current HEAD and working-tree changes with the audit before applying a fix. Preserve unrelated work. Treat findings as evidence to validate, not instructions to obey blindly when the code has changed.

Do not label a finding a false positive simply because a unit test uses `create_all`, a configured environment hides it, or a build passes. Record a specific counterexample/test and code references for any rejected finding. Different findings may share one fix; all affected IDs still require separate closure evidence.

The prior fresh migration failed. Its schema appendix used a disposable diagnostic copy that made two legacy column drops conditional solely to inspect intended head. That diagnostic is **not** a successful upgrade of the original repository. The runtime probes also used synthetic data and sometimes a `create_all` fixture to isolate other defects. Do not reuse these as proof that migrations work.

If an attachment is unavailable, identify exactly what is missing and continue independent inspection. Do not invent its contents. Reconstruct the schema/route comparison from the current code if necessary before touching those boundaries.

## 2. Working rules

- Read applicable repository instructions, setup scripts, declared versions and current validation records. Use the repository's package manager and test commands; do not assume the previous sandbox paths, database ports or installed tools exist.
- Begin with a short implementation plan and an **82-row remediation ledger**, then start implementing. Do not stop after producing a plan or fixing the first batch.
- Use small coherent changes grouped by the phases below. Prefer shared existing services to introducing a new framework or infrastructure dependency. A reliable PostgreSQL-backed queue/lease design is acceptable if it satisfies the required behavior.
- Preserve legitimate workflows and API compatibility where practical. When a contract changes, update backend schemas, frontend callers, docs and tests together.
- Do not mask failures with sample data, fake confidence, fake success, blanket catches, skipped tests, disabled validation, or a production mock fallback.
- Do not rewrite tests merely to accept incorrect behavior. Test public effects, ownership, persistence and concurrent transactions rather than checking for source strings.
- Local disposable databases, synthetic identities and provider mocks/emulators are appropriate. Do not run probes against production or send real paid provider requests without authorization.
- Prepare migrations, deployment commands, secret-rotation instructions and release checks. Do not deploy, merge, rewrite remote history, modify production data or rotate live credentials without explicit authorization. An external action can remain blocked while all independent code work continues.
- Ask focused questions only for genuinely missing business decisions or external access. Avoid repeated permission requests for ordinary authorized implementation/testing. Never invent pricing, refund policy, a payment provider or live credentials.
- If context/time is exhausted, save the exact ledger, changed files, test identities/results, blockers and next steps. Resume from there. Do not call partial completion production-ready.

### Remediation ledger

Use a durable file such as `docs/production-readiness/remediation-status.md` plus JSON if useful. One row per F01–F82, with:

`ID | original severity | current reproduction | root cause | changed files | migration/config impact | regression test | observed test result | status | external follow-up`

Allowed statuses:

- `OPEN`
- `IN_PROGRESS`
- `FIXED_VERIFIED` — relevant behavior passed meaningful tests on the current patch.
- `ALREADY_FIXED_VERIFIED` — current code already addresses it, confirmed with evidence.
- `DISPUTED_WITH_EVIDENCE` — the report was wrong or no longer applies; include reproducible evidence.
- `MITIGATED_FEATURE_DISABLED` — an unfinished capability is explicitly unavailable at API and UI levels. This is containment, not feature completion.
- `BLOCKED_EXTERNAL` — code-independent action needs access/authorization or a business decision; identify the owner/action and any completed local fix.

A changed file, successful build, or disabled feature alone does not qualify as `FIXED_VERIFIED`.

## 3. Implementation phases

Work in dependency order. Contain a critical exposure immediately when practical, while keeping the schema and regression foundation first in the dependency plan. Related fixes may cross phases; preserve a coherent model and ledger.

### Phase 1 — Schema, startup and regression gates

**F01, F13, F14, F15, F16, F62, F74, F77**

- Compare all model tables/columns/types/nullability/defaults/indexes/FKs/uniques with the full Alembic chain. Reconcile the audit's 14 missing tables, 24 missing columns, 34 server-default differences and 3 nullability differences, plus newly discovered current drift.
- Preserve the distinction between a Python default and a database default. Choose the intended contract explicitly; align metadata and migration behavior instead of blindly dropping defaults to silence a check.
- Repair fresh upgrades that fail on nonexistent legacy columns. Prefer forward migrations for deployed data. If broken historical DDL prevents reaching any new revision, document the minimal compatibility edit, account for databases where the revision was already applied, and test both histories. Never assume an applied revision will rerun.
- Use expand/backfill/validate/contract steps where needed. No destructive reset, blind column/table drop, data deletion or `alembic stamp head` to conceal drift.
- Remove production `create_all` and raw startup ALTER repair loops. Run migrations through one explicit deployment/release step with appropriate locking and failure behavior. Leave application replicas responsible for serving compatible schemas, not racing to change them.
- Separate liveness and readiness. Return 503 when required DB/schema dependencies are unavailable or incompatible. Exercise representative ORM access and migration compatibility so SELECT 1 cannot hide another signup outage. Keep sensitive diagnostics restricted.
- Enforce the default-organization uniqueness invariant with safe concurrent creation, without accidentally forbidding legitimate multiple workspaces.
- Lock tested backend and worker dependencies/browser versions. Keep the declared frontend lockfile toolchain.
- Add PostgreSQL CI for fresh upgrades, upgrade from supported pre-change/deployed states, preserved existing data, and `alembic upgrade head && alembic check`, including server-default comparison. Tests must not hide drift through startup DDL or create_all.

### Phase 2 — Authentication, sessions and credential protection

**F02, F17, F18, F19, F20, F21, F22, F52, F59, F60, F76**

- Remove plaintext password fallback; reject external-auth markers and unsupported formats. Retain explicitly supported legitimate legacy hashes safely.
- Wire real reset-email delivery through the existing email abstraction. Keep account enumeration protections and remove tokens/reset URLs from logs/responses in production.
- Make reset tokens unpredictable, expiring and atomically single-use. Concurrent redemption must have exactly one winner; an old token must not invalidate a newer one. Apply one password policy across signup/reset/profile.
- Design and implement session revocation/rotation so logout, password reset and relevant security changes revoke the intended sessions. Existing sessions need an explicit migration/expiry strategy.
- Address bearer-token exposure in browser storage with a coherent browser/API authentication design. If using HttpOnly cookies, handle Secure/SameSite/domain/CORS/credentials/CSRF for separate Vercel/API origins; retain intentional API-key authentication. Test impersonation and all API clients against the chosen design.
- Rotate-capable JWKS caching: TTL, refresh on unknown kid, appropriate issuer/audience/required-claim validation. Verify the actual configured Neon token contract; do not assume arbitrary claims are present.
- Remove committed provider credentials and dangerous admin fallback passwords. Prepare rotation/history-remediation instructions and an external action checklist; deleting a literal is not proof its credential was revoked.
- Encrypt stored Scout secrets using the credential abstraction, including a safe migration from plaintext flags. Do not expose secrets in logs, responses, query strings or VITE variables. Use a separate scoped diagnostic credential, not the JWT signing key.

### Phase 3 — Tenant, workspace and administrative authorization

**F03, F04, F05, F06, F12, F46, F47, F48, F53, F61, F80**

- Define one principal/workspace authorization model for owners, accepted members, API keys and authorized staff. Membership must actually grant the intended shared workspace access; an API key's org and scopes must survive authentication.
- Trace every route and service query, including aliases, saves, exports, AI generation, simulation, pattern generation, playbook compilation/publication, brands, counts and aggregates. Scope before reads, writes, provider calls or charges.
- Fix global fallback selections; an empty authorized result must never switch to another tenant's records. Use keyword arguments for corrected pattern contracts and enforce its feature/credit gate.
- Separate authenticated app updates from public-visible updates. Verify intended publication and source ownership before producing public playbooks.
- Deliver real invitations, bind redemption to the intended verified identity, enforce expiry/single use atomically, and uniquely constrain membership. Wire acceptance and workspace selection through the UI.
- Enforce granular admin permissions on the server, preserving full-admin requirements for sensitive mutations and impersonation audit trails.
- Recheck API entitlements after plan changes/revocation. Clear or namespace every tenant-sensitive cache, draft and persisted browser state when identity/workspace changes.

**Required isolation matrix:** owner A, member of A, unrelated owner B, admin, restricted assistant-admin, valid scoped API key, revoked key, downgraded key, anonymous caller. Exercise guessed IDs, known foreign IDs, empty filters, missing job IDs, list totals, writes and public publication.

### Phase 4 — Credits, quotas and idempotency

**F07, F08, F10, F11, F27, F28, F32, F50, F55**

- Establish explicit billing invariants: balances cannot overspend; a logical operation reserves once and settles once; each reversal refers to a real debit/reservation and cannot exceed it; counters and ledger remain consistent.
- Use conditional atomic SQL/appropriate row locks and database uniqueness constraints. Account for SQLAlchemy identity-map staleness and transaction boundaries. Do not clamp balances to zero to hide an overdraw.
- Reserve funds/quota and create the durable job transactionally. Commit before slow provider work. Settle or release exactly once afterward; do not hold an org lock across HTTP calls.
- Implement tenant-scoped idempotency keys with request fingerprints and persisted outcomes for paid/state-changing operations. Replays return the same operation; reusing a key with different input is rejected. Limit frontend automatic retries accordingly.
- Enforce user budgets, plan flags, expiry, daily limits, custom entitlements and in-flight media limits server-side. Upgraded users must not remain under trial-only AI gates. Handle concurrent resets/day boundaries consistently.
- Bring leadgen into the same ledger and admission rules; never replace a user ceiling with a larger computed cost. Replace the racy hard-coded global 20-attempt cap with configurable, atomic capacity controls and tenant fairness.
- Implement explicit failure/partial-result/cancellation billing policy. Refund unused reservations consistently; no fabricated or failed provider response may count as a successful charge. Escalate genuinely unspecified partial-consumption policy before enabling paid use.

**Required race/crash tests:** multiple simultaneous jobs with insufficient total balance; concurrent image/video admissions; same idempotency key retried after lost response; two sweepers; repeated refund; stale ORM instances; crash between every job/ledger transition. Use separate real PostgreSQL sessions/processes and synchronization barriers where needed. Prove exactly-once financial effects even if work execution retries.

### Phase 5 — Durable jobs and worker execution

**F24, F25, F26, F30, F40, F65, F70, F82**

- Keep one async event loop for the Scrapling worker's async engine/session lifetime; dispose it cleanly on shutdown.
- Put critical work behind durable claims/leases. Cover discovery, media, Scout, Maps, leadgen and monitor workflows, with SKIP LOCKED or equivalent atomic claiming, heartbeat renewal, deadlines, bounded attempts and recovery.
- Do not mark a fresh-heartbeat job dead merely because it is old or another instance starts. Recover abandoned tasks within the same process as well as after process death.
- Base admission on real worker health/capacity and defined queue semantics, not only an enabled flag. Expire/refund work that cannot execute within its SLA.
- Wrap the entire task, including credential/provider resolution, in terminal-state handling. No error may leave a job pending forever.
- Implement real pause/resume with refreshed control fields and durable checkpoints; queue status must not erase resume intent. Keep checkpoints portable across workers or explicitly constrain ownership safely.
- Make cancellation a guarded state transition, including provider cancellation where available and defined handling of unavoidable provider completion. A late task cannot silently overwrite cancellation or settle twice.

**Required failure injection:** kill/restart the API/worker after enqueue, claim, provider completion and before settlement; run two workers/reconcilers; rotate credentials to induce resolution failure; pause/resume while crawling; cancel during provider work. Assert terminal/recoverable state and ledger invariants.

### Phase 6 — Providers, output integrity and durable media

**F09, F23, F29, F31, F38, F39, F41, F49, F54, F66, F81**

- Fix default provider initialization and adapter signature mismatches. Contract-test every provider through the actual shared caller.
- Represent success, verified empty results, partial results, unsupported capability, timeout, auth failure, 429 and provider outage separately. Use bounded retries/backoff/jitter/Retry-After where safe and avoid duplicate provider spend.
- Remove fabricated analysis/confidence/conversion claims. Offline heuristics, if retained, require explicit labeling, provenance and separate billing semantics. Do not swallow failure and return a successful invented result.
- Persist complete paid insight responses and restore them without regeneration charges. Version schemas/models and retain evidence/provenance.
- Only update monitor inventories or issue stopped-ad alerts from sufficiently complete successful snapshots. Provider failure must preserve prior evidence.
- Derive the media catalog from real configured adapters. Implement frame/reference/XHR features end-to-end or explicitly reject and disable unsupported choices at API and UI. Track disabled features as mitigated, not implemented.
- Centralize safe outbound URL handling: supported schemes, validated DNS A/AAAA results, IPv4-mapped IPv6, redirect chains, rebinding resistance and browser subrequests. Restrict egress as appropriate. Test with local controlled servers/mocked DNS; never probe real cloud metadata.
- Bound downloads, uploads, robots fetches, sitemap recursion, response sizes, decompression/image decoding, browser concurrency and total execution duration.
- Require durable production R2 configuration and a successful storage operation before reporting generation success. Restrict ephemeral disk to explicit development. Test object retrieval and declared media types with synthetic files.

### Phase 7 — Frontend and broken user flows

**F33, F34, F35, F36, F37, F42, F43, F44, F45, F51, F56, F57, F68, F69, F73, F75**

- Repair custom swipes with valid ownership/relations and unknown metrics; avatar uploads through the real validated storage interface; populated support listing; Performance calculations; missing notification icon; canonical playbook job IDs; impersonation identity switching.
- Remove production sample history, canned unrelated translations, fake metrics and synthetic success after backend errors. Fail closed on invalid production data-source configuration.
- Review every page/data-fetching component against loading, empty, populated, failed, unauthorized, denied and retry states. A 500 must not become empty data; failed saves need rollback; initial session loading always resolves to a usable state.
- Make polling single-flight, bounded and abortable. Old requests cannot mutate a new job/account's state or restart polling after unmount. Avoid blanket “server waking” messages for known provider/worker failures.
- Normalize datetime contracts end-to-end and convert timezones before dropping timezone information, if naive storage is intentionally required.
- Exercise desktop/mobile and English/Arabic RTL in a browser. Fix keyboard access, labels, focus containment/restoration, dialog behavior, contrast and overflow with measured evidence. Preserve legitimate navigation and empty states.

**Required browser journeys:** signup/sign-in/reset/profile/avatar; account switch; discovery → detail → insight → saved creative → playbook; image/video generation and cancellation; support with tickets; populated Performance and notifications; team invite/accept/switch; admin impersonation/exit. Test errors and nonempty data, not just the landing page.

### Phase 8 — Operational, analytics and code-health closure

**F58, F63, F64, F67, F71, F72, F78**

- Use shared bounded rate-limit state and trusted proxy IP interpretation; cover aliases and every expensive/auth flow. Multi-instance/restart behavior and actual reverse-proxy configuration need explicit tests/documentation.
- Add supporting indexes from actual tenant/job/queue queries, bounded pagination and batch aggregates. Use representative query plans; do not indiscriminately index every field. Eliminate the identified N+1/unused counts.
- Neutralize spreadsheet formula injection in every CSV export without corrupting ordinary data.
- Keep analytics entirely disabled when unconfigured. Verify configured delivery/counts, pageview ownership and privacy with a test collector/mocked script before using live analytics. Do not assert duplicate pageviews without testing the selected script behavior.
- Capture all supported UTM fields, including term/content-only visits; bound/allowlist attribution and strip sensitive referrer queries/fragments. Avoid PII in analytics and logs; clear attribution only after successful registration.
- Add consistent machine-readable errors, useful structured correlation logs and appropriate error tracking hooks without secrets/payload dumps. Make observed failure states actionable.
- Remove tracked generated dist and confirmed dead code; consolidate duplicated entitlement/fallback logic. Break large modules along behavioral boundaries where useful without arbitrary rewrites or a cosmetic line-count target. Update setup/env/deploy docs and the TODO inventory.
- Measure worker/browser resource use against the intended deployment, including the 512 MB target if retained. Do not claim capacity was verified from source or configuration alone.

### Phase 9 — Payments and release closure

**F79**, plus regression verification of **all F01–F82**.

Inspect whether a real payment integration now exists. If the provider/product decisions are known, implement its server-verified checkout/settlement/subscription/invoice lifecycle, signed webhooks, replay protection, refunds/reconciliation and the corresponding UI using sandbox mode first. Never grant credits based solely on a client success redirect.

If provider, pricing/tax/renewal policy or authorization is missing, ask a focused question early and continue all independent work. Prepare interfaces, tests, migrations and a concrete integration plan where possible. Keep purchase/renewal UI honest and disabled until fulfillment is implemented and verified. Record `BLOCKED_EXTERNAL` or `MITIGATED_FEATURE_DISABLED`; do not count a renamed label as completing paid billing.

## 4. Verification and completion criteria

Maintain a validation record with exact command, cwd, relevant source/config/lockfile identities, runtime versions, service/fixture state, result and observed exit status. Reuse unchanged valid results; rerun checks when relevant inputs change. Preserve failed/blocked checks instead of replacing them with build success.

Required release gates, using repository-equivalent commands:

1. Fresh PostgreSQL upgrade, supported existing-state upgrades and data-preservation assertions.
2. `alembic upgrade head && alembic check` with model/default consistency; no production startup DDL required to pass.
3. Readiness returns 503 for DB/schema incompatibility and liveness has an intentionally separate contract.
4. Behavioral auth/session/reset/tenant/API-key/admin tests, including every demonstrated exploit.
5. Real PostgreSQL concurrency/idempotency/ledger tests and failed-job settlement checks.
6. Durable worker multi-instance/crash/recovery tests, including repeat queue polls on one engine.
7. Provider contract and network-boundary tests with success, empty, partial, malformed, timeout, 429 and failure fixtures.
8. Frontend production build, undefined-name/static checks and nonempty/error-state component tests.
9. Critical browser journeys, English/Arabic RTL and keyboard accessibility checks.
10. Secret scanning, production-config rejection tests, CSV safety and analytics privacy/disabled-path tests.
11. Meaningful resource/load checks for the intended deployment; record unsupported runtime conditions explicitly.
12. Live/staging integration checks that require credentials/access remain separately identified until actually run. An emulator pass proves local contract behavior, not deployed provider correctness.

Use the provided probes as starting evidence. Adapt hard-coded paths, seed IDs, tool versions and database setup into isolated repeatable tests. Never copy old audit logs as new validation results.

### Final report format

A. **Completion verdict:** all findings addressed or incomplete; production-ready YES/NO with concrete remaining gates.
B. **82-row closure table:** every F01–F82, status, changed file:line, test and observed result, remaining external action. Do not provide only a sample or only the last phase.
C. **Implementation summary by subsystem:** actual changes and intentional compatibility impacts.
D. **Migrations and release runbook:** preflight, backups/restore prerequisites, schema compatibility, deployment ordering, exact commands, smoke checks, rollback/roll-forward and recovery limits.
E. **Validation:** passed, failed, blocked and unexecuted checks; distinguish reused results from fresh runs and local fixtures from real integrations.
F. **Credential/operational actions:** what was removed locally, what still requires rotation/access, and whether that action actually happened.
G. **Unfinished capabilities/business decisions:** distinguish implemented, safely disabled, disputed and externally blocked work.
H. **Reviewable delivery:** branch/commits or patch, any PR link if authorized, remediation ledger, tests and docs. The original empty-base audit PR remains separate.

Do not say “all fixed” while findings are merely documented, hidden, disabled, untested or awaiting external work. Continue through all independently executable work. Finish only with a verifiable delivery and an honest account of anything still incomplete.

## 5. Complete finding-to-phase checklist

This embedded index prevents missing a finding when the attached report is long. It is not a substitute for each finding's full reproduction, supporting references and fix in `findings.json`.

| ID | Severity | Phase | Finding | Original source |
|---|---|---|---|---|
| F01 | P0 | 1 | The incident class remains: models and migrations describe different databases. | `backend/app/models/user.py:23` |
| F02 | P0 | 2 | A shared external-auth marker is a working password. | `backend/app/core/security.py:124` |
| F03 | P0 | 3 | Saving a foreign creative bypasses the scoped creative GET. | `backend/app/services/creative_service.py:400` |
| F04 | P0 | 3 | Playbook compilation publishes other tenants’ data. | `backend/app/services/playbook_service.py:49` |
| F05 | P0 | 3 | Brand and pattern lists are global. | `backend/app/api/routers/creatives.py:96` |
| F06 | P0 | 3 | Insight/simulation creation accepts foreign creative IDs. | `backend/app/services/analysis_service.py:34` |
| F07 | P0 | 4 | Concurrent charges lose deductions despite FOR UPDATE. | `backend/app/services/billing_service.py:305` |
| F08 | P0 | 4 | Refunds can mint credits or be lost permanently. | `backend/app/services/billing_service.py:345` |
| F09 | P0 | 6 | Provider outages produce charged fabricated analysis. | `backend/app/services/ai/base.py:60` |
| F10 | P0 | 4 | Transport retries replay paid mutations. | `src/services/http.js:96` |
| F11 | P0 | 4 | Concurrent media jobs bypass generation quotas. | `backend/app/services/media_service.py:243` |
| F12 | P0 | 3 | Workspace data survives account changes in the same browser. | `src/context/SearchContext.jsx:3` |
| F13 | P1 | 1 | A fresh alembic upgrade fails. | `backend/alembic/versions/46af201944fd_add_is_suspended_to_users.py:24` |
| F14 | P1 | 1 | Startup changes schema outside Alembic and continues after schema errors. | `backend/app/main.py:45` |
| F15 | P1 | 1 | Health reports success during DB/schema outages. | `backend/app/api/routers/health.py:23` |
| F16 | P1 | 1 | The existing gates cannot catch the reported incident or runtime name errors. | `.github/workflows/ci.yml:35` |
| F17 | P1 | 2 | Forgot-password sends no email and logs the usable reset token. | `backend/app/api/routers/auth.py:204` |
| F18 | P1 | 2 | Reset tokens are not atomically single-use; stale links invalidate new links. | `backend/app/services/auth_service.py:159` |
| F19 | P1 | 2 | Logout and password resets do not revoke stolen sessions. | `backend/app/api/routers/auth.py:183` |
| F20 | P1 | 2 | Meta access-token literals are committed. | `backend/scripts/inspect_meta_token.py:6` |
| F21 | P1 | 2 | Scout credentials are stored as plaintext JSON. | `backend/app/api/routers/scout.py:690` |
| F22 | P1 | 2 | BYOK credentials and the JWT signing secret are accepted in query strings. | `src/services/api/analysisService.api.js:18` |
| F23 | P1 | 6 | URL guards allow private network fetches. | `backend/app/services/leadgen_pipeline.py:122` |
| F24 | P1 | 5 | The worker reuses async database connections across destroyed event loops. | `backend/workers/scrapling/worker.py:126` |
| F25 | P1 | 5 | Background tasks are not a durable queue; Scout/Maps/leadgen lack dead-job recovery. | `backend/app/api/routers/scout.py:113` |
| F26 | P1 | 5 | An enabled flag is treated as a live worker. | `backend/app/api/routers/leadgen.py:190` |
| F27 | P1 | 4 | Leadgen bypasses billing policy and overwrites the user’s spend ceiling. | `backend/app/api/routers/leadgen.py:259` |
| F28 | P1 | 4 | Failed Scout/Maps/leadgen jobs retain their upfront charges. | `backend/app/services/scout_service.py:193` |
| F29 | P1 | 6 | Provider failure is reported as a successful empty search and charged. | `backend/app/services/scraping/ad_library_provider.py:202` |
| F30 | P1 | 5 | Pause uses a stale object and resume never selects the checkpoint path. | `backend/app/services/leadgen_pipeline.py:401` |
| F31 | P1 | 6 | Default AI provider construction raises NameError. | `backend/app/services/ai/ai_router.py:23` |
| F32 | P1 | 4 | Upgraded users remain subject to expired-trial AI gates. | `backend/app/services/ai/ai_router.py:101` |
| F33 | P1 | 7 | Custom swipe creation always fails. | `backend/app/services/creative_service.py:527` |
| F34 | P1 | 7 | Avatar upload calls a nonexistent storage function. | `backend/app/api/routers/account.py:90` |
| F35 | P1 | 7 | Performance crashes as soon as it has data. | `src/pages/PerformancePage.jsx:205` |
| F36 | P1 | 7 | Opening a nonempty notification menu crashes rendering. | `src/components/NotificationBell.jsx:238` |
| F37 | P1 | 7 | Support ticket listing fails once a ticket exists. | `backend/app/services/support_service.py:70` |
| F38 | P1 | 6 | Every Gemini BYOK image call has an invalid argument. | `backend/app/services/media_service.py:165` |
| F39 | P1 | 6 | Advertised media provider/mode capabilities are not wired through. | `backend/app/api/routers/media.py:31` |
| F40 | P1 | 5 | Canceled media jobs can become completed and consume quota. | `backend/app/api/routers/media.py:66` |
| F41 | P1 | 6 | Paid detailed insight fields disappear after reload. | `backend/app/services/analysis_service.py:93` |
| F42 | P1 | 7 | Intelligence invents output after errors and substitutes unrelated translations. | `src/pages/IntelligencePage.jsx:346` |
| F43 | P1 | 7 | New accounts are given fictional search history. | `src/context/SearchContext.jsx:22` |
| F44 | P1 | 7 | The UI drops the search job ID when compiling a playbook. | `src/pages/IntelligencePage.jsx:407` |
| F45 | P1 | 7 | A transient session failure can leave the app loading forever. | `src/context/AuthContext.jsx:54` |
| F46 | P1 | 3 | Team invitations report delivery but shared workspaces do not work. | `backend/app/services/team_service.py:109` |
| F47 | P1 | 3 | An invitation is not bound to its intended email or consumed atomically. | `backend/app/services/team_service.py:129` |
| F48 | P1 | 3 | App-only updates are exposed by public APIs. | `backend/app/api/routers/updates.py:30` |
| F49 | P1 | 6 | Production media falls back to ephemeral storage on incomplete R2 configuration. | `backend/app/services/storage_service.py:77` |
| F50 | P1 | 4 | Twenty provider attempts disable discovery for every tenant. | `backend/app/services/api_usage_service.py:9` |
| F51 | P1 | 7 | The impersonation UI keeps using the administrator token. | `src/pages/admin/UsersPage.jsx:125` |
| F52 | P1 | 2 | The admin seeder has a public fallback password. | `backend/scripts/seed_admin.py:18` |
| F53 | P1 | 3 | Pattern generation has shifted arguments, global data selection and no credit gate. | `backend/app/api/routers/creatives.py:121` |
| F54 | P1 | 6 | Provider outages can create false “ad stopped” alerts. | `backend/app/services/monitor_service.py:500` |
| F55 | P1 | 4 | Configured per-plan image/video limits are ignored. | `backend/app/services/billing_service.py:625` |
| F56 | P1 | 7 | Exported playbooks invent confidence and performance lift. | `src/pages/DashboardPage.jsx:88` |
| F57 | P1 | 7 | Failed reads/saves are displayed as success, empty data or a waking server. | `src/hooks/useLeadGenJob.js:55` |
| F58 | P2 | 8 | Rate limits are spoofable in the app, instance-local and incomplete. | `backend/app/middleware/rate_limit.py:58` |
| F59 | P2 | 2 | JWKS cache never refreshes. | `backend/app/core/security.py:22` |
| F60 | P2 | 2 | Profile password changes bypass signup/reset length checks. | `backend/app/api/routers/account.py:60` |
| F61 | P2 | 3 | Issued API keys outlive the public_api entitlement and lose workspace scope. | `backend/app/services/api_key_service.py:88` |
| F62 | P2 | 1 | Default-organization creation races. | `backend/app/services/billing_service.py:83` |
| F63 | P2 | 8 | Hot tenant/job/filter queries lack supporting indexes. | `backend/app/models/scrape_job.py:13` |
| F64 | P2 | 8 | Several lists are unbounded; support adds an N+1 count query. | `backend/app/services/support_service.py:60` |
| F65 | P2 | 5 | LLM work holds an organization row lock inside a request. | `backend/app/services/analysis_service.py:41` |
| F66 | P2 | 6 | Fetch/upload paths have unbounded time, recursion or memory use. | `backend/app/services/scrapling_engine.py:59` |
| F67 | P2 | 8 | Scraped strings can become spreadsheet formulas. | `backend/app/api/routers/scout.py:323` |
| F68 | P2 | 7 | Polling overlaps requests and stale failures can cancel a newer job. | `src/hooks/useDiscoverySearch.js:120` |
| F69 | P2 | 7 | Datetime serialization and scheduling lose timezone correctness. | `backend/app/services/team_service.py:70` |
| F70 | P2 | 5 | Starting another instance can fail a live long-running job. | `backend/app/main.py:126` |
| F71 | P2 | 8 | Unvalidated attribution can carry PII into analytics and logs. | `src/lib/utm.js:54` |
| F72 | P2 | 8 | Term/content-only UTM visits are dropped. | `src/lib/utm.js:29` |
| F73 | P2 | 7 | Keyboard/focus and label contracts are incomplete. | `src/components/ui/ConfirmDialog.jsx:25` |
| F74 | P2 | 1 | Backend/worker deploys resolve unbounded dependency versions. | `backend/requirements.txt:1` |
| F75 | P2 | 7 | Invalid data-source configuration silently enables mock mode. | `src/services/config.js:14` |
| F76 | P2 | 2 | Long-lived bearer tokens are readable by every script on the origin. | `src/services/api/authService.api.js:41` |
| F77 | P3 | 1 | Additional default/nullability differences make creation paths inconsistent. | `backend/app/models/leadgen.py:58` |
| F78 | P3 | 8 | Generated artifacts, large modules and duplicated fallback/billing logic raise drift risk. | `dist/index.html:1` |
| F79 | P1 | 9 | Paid plans display “Monthly renewal” without a subscription lifecycle. | `src/pages/BillingPage.jsx:36` |
| F80 | P1 | 3 | Stored granular admin permissions do not restrict access. | `backend/app/services/admin_service.py:633` |
| F81 | P1 | 6 | The XHR-capture option is accepted and stored but never implemented. | `backend/app/services/scrapling_engine.py:80` |
| F82 | P1 | 5 | Provider-resolution failures leave media jobs pending indefinitely. | `backend/app/services/media_service.py:117` |
