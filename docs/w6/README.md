# W6 — verification and handoff

**Draft PR into `fix/intelligence-W5`; do not merge or deploy.** W6 starts at W5 `f7673e9`. Part A is blocked; green tests are not real-provider proof or production readiness. No pricing, checkout, billing purchase flow, dependency upgrade, RLS relaxation, or fabricated provider output was added.

The read-first W5 documents and audit were consulted. `DESIGN_SYSTEM.md` is absent; existing `src/styles/globals.css` tokens/UI primitives were retained. The audit was read from `audit/helix-full`, not copied into the application.

## A — Discover through the durable worker: BLOCKED / STOPPED

Presence-only checks found no authorized non-production Discover credentials (`METAPI_API_KEY` and supported aliases, `ADYNTEL_API_KEY`/`ADYNTEL_EMAIL`, `APIFY_API_TOKEN` and alias, `META_ACCESS_TOKEN`, `BRIGHTDATA_API_KEY`). No provider call or durable worker was intentionally started. The synthetic local launcher explicitly disables optional provider integrations.

**Not proved:** provider-backed success and stored real results; immediate terminal work-item cleanup after success/cancel/timeout; interruption/crash/reclaim; stale-worker fencing and duplicate delivery against an actual provider. PostgreSQL regressions use controlled provider coroutines, not live-provider results. They cannot close A.

**Single P0 next step:** supply an authorized **non-production** provider key through approved secrets, then run API → durable outbox/worker → provider and verify real persisted results, interruption, cancellation/timeout cleanup, fencing and duplicate delivery. Do not substitute browser mocks, manual status changes, production credentials, or weakened checks.

## B — access, localization, dates and mutations

- Admin users/organizations now show explicit pending, admin-granted, revoked, inactive or unavailable access state, independently of account role and legacy plan names. No plan is presented as a purchasable entitlement.
- Admin overview, users, organizations, access requests, support, updates and audit-log templates have EN/AR copy. Member settings, support and notifications use localized page copy and extracted service hooks. Technical documentation retains its existing English-content disclosure.
- Backend admin timestamps serialize valid UTC `Z` values. UI formatters use the selected locale and safely render absent/invalid dates rather than `Invalid Date`.
- Authorized admin role/status/flag/access/impersonation/update actions now write audit records in the mutation transaction. Support queries/replies enforce tenant ownership and explicit support permission. Publishing requires a full administrator. Profile/avatar/password writes require a workspace audit context; no-workspace UI hides these writes with an explanation instead of inviting a predictable 409.
- Profile save handles the backend's nested `user` response. A successful password change clears the revoked session and asks the user to authenticate again.
- Real avatar verification found that local storage issued a URL without writing bytes. W6 writes the file, stores its stable reference, and resolves a short-lived user/token-version-bound capability after authorization. The development proxy forwards `/uploads` to the existing guarded backend endpoint; it does not make uploads public.

### Mutation evidence and limits

| Surface | Confirmed evidence | Not claimed |
| --- | --- | --- |
| Role / ban | Browser changed the synthetic other-user role, banned it, reloaded the banned state, then unbanned it. Local SQL confirms customer/unbanned and audit entries. | Production-account behavior |
| Credits | Browser grant changed the member balance from 28 to 30; persisted after direct reload. SQL and grant audit rows agree. | Billing/checkout or real monetary transactions |
| Grants / revoke / decisions / flags / organization status | Real PostgreSQL tests check writes, audit, denied permissions, cross-tenant isolation and rollback behavior. Earlier synthetic preview grant/revoke rows are retained separately. | A final browser interaction for every action |
| Impersonation / public updates / support | PostgreSQL tests cover authorization, audit and persistence; all admin pages load in the route matrix. | Every impersonation/support/publishing flow end-to-end in the final browser pass |
| Profile / avatar | Browser saved a synthetic name, uploaded a real generated PNG, reloaded, and confirmed the image loaded from the same origin. | R2/object-storage persistence; local disk is ephemeral |
| Password | Browser changed the password, observed sign-out, and logged in using the new password. SQL contains the audited profile write. | Email reset delivery or external identity providers |
| No-workspace / failure cases | Focused UI/service tests cover hiding writes and failure messages; PostgreSQL tests cover denied and cross-tenant mutations. | A separate final browser fixture for every failure branch |

See [profile evidence](evidence/profile-browser.json), [current SQL](evidence/mutations-final-sql.txt), [earlier SQL](evidence/mutation-baseline-sql.txt) and `backend/tests/test_intelligence_w6_admin_mutations.py`. Passwords, tokens, raw network headers and browser state are not included.

## C — navigation, tour and responsive regression

The bounded matrix covers visible public documentation/articles and policy pages, member Discover/access/support/settings/notifications, and all seven visible admin pages in EN/AR at **1280×800** and **390×844**. It records direct-load path/title/lang/dir, overflow, invalid dates, error boundaries, dialogs, failed requests, console/uncaught errors and duplicate API reads. This is route-level evidence, not proof of all controls or provider-dependent data states.

| Matrix | Result | Evidence |
| --- | --- | --- |
| Public | **120 / 120 passed** | [public](evidence/routes-public.json) |
| Admin | **28 / 28 passed** | [admin](evidence/routes-admin.json) |
| Member | **20 / 20 passed after onboarding completion** | [member](evidence/routes-member.json) |

The first member sweep correctly encountered the new-user questionnaire on all four Discover states (16/20 unobstructed route checks). Closing it persisted after refresh; the later sweep is after explicit dismissal/completion, not a suppressed assertion. The first public sweep exposed mobile article overflow and duplicate anchor IDs; W6 fixed heading IDs/TOC agreement and mobile section navigation. Documentation-section redirects use their actual canonical article paths.

The application now coalesces identical in-flight GETs by URL, headers/session and retry/timeout policy, clearing them on settlement and not sharing independently abortable requests. This removes the observed simultaneous banner reads without caching mutations or crossing users. Periodic refreshes, HMR and separate sequential loads are not claimed to be globally deduplicated.

Tour/history evidence is in [tour-history.json](evidence/tour-history.json). Desktop checks cover settings restart, skip/close, sidebar restart, finish and refresh persistence, with one overlay and no competing questionnaire. Mobile/Arabic, drawer cleanup and member back/forward results are recorded separately in that artifact. Public browser checks also exercised direct refresh, back/forward and the mobile docs drawer. No provider query was submitted from the wizard.

## D — weight and application-owned warnings

Landing and admin shell use the existing safe lazy loader. Discover stays reachable through the authenticated shell. Public documentation imports only published article directories, not internal W4/W5/audit reports. No bundler threshold was raised and no warning filter was added.

Raw bytes / gzip-9 bytes (gzip summed per emitted JS chunk; not a measured network transfer):

| Measure | W5 baseline | W6 final application build |
| --- | ---: | ---: |
| Entry JS | 508,269 / 155,971 | **490,270 / 152,027** |
| Initial Discover static graph | 598,370 / 186,214 | **583,116 / 184,166** |
| All emitted JS | 1,372,079 / 414,975 | **1,289,299 / 401,328** |

[Machine-readable measurement](evidence/bundles-final.json). The final build emits no >500 kB chunk warning. The entry remains substantial; this is a measured incremental split, not a claim of optimal performance.

Removed scoped application warnings: legacy Pydantic class configuration/dict calls, SQLAlchemy declarative import, naive UTC datetime calls and pytest-asyncio loop-scope defaults. The durable-job test's unawaited `AsyncMock` was caused by modeling synchronous result mappings as async; the fixture now returns realistic synchronous results without weakening assertions. Third-party Vitest/jsdom prints a performance advisory; no unrelated runner/dependency upgrade was made. Local media intentionally warns that disk is ephemeral and is not production storage.

## Verification

- Disposable PostgreSQL backend: **255 passed, zero skips**, `python -m pytest -q tests -W error` (includes one real local-avatar-storage regression; no live provider tests).
- Backend `compileall` and `pyflakes app`: passed.
- Disposable Alembic: upgrade head → downgrade one → upgrade head → `alembic check`: passed; no drift. Separate loopback database, not the preview database.
- Frontend: `pnpm typecheck`, `pnpm lint` (zero warnings), `pnpm test`: passed (**5 Node tests + 188 Vitest tests / 35 files**).
- `pnpm build --manifest`: passed; bundle figures above are from this final application build. Generated build/doc metadata was not committed.
- `git diff --check`: passed before evidence publication; final-head CI is recorded in the PR and must not be inferred from earlier W6 checks.

The test database uses a disposable local owner for setup. Preview API runs as `NOSUPERUSER NOBYPASSRLS` and inherits the existing application role. PostgreSQL isolation regressions verify app-role tenant denial; no RLS policy or authorization gate was relaxed. [Preview setup](preview-setup.md) is repository-owned and generated credentials are ignored.

### Boundaries and remaining defects / unverified areas

1. **P0: Part A remains blocked.** W6 cannot be described as provider-proved or production-ready.
2. **Incomplete browser mutation coverage:** the table above explicitly distinguishes DB-tested actions from final interactive proof. Failure UI, no-workspace fixtures, R2, email delivery and every modal/control are not fully browser-proved.
3. During avatar investigation, an inherited production media-origin default caused the browser to attempt an external image request for a synthetic local filename; it did not render. This was not an authorized production test. The preview now explicitly uses same-origin `/api` media signing and a guarded local `/uploads` proxy; subsequent avatar proof is loopback-only. No production credentials, production database or production account was used.
4. Local media/database/identities are disposable. This preview does not provide durable production storage, email delivery or provider readiness.
5. Route smoke checks do not establish accessibility certification, realistic provider-result layouts, every deep-link/data combination, or absence of all bugs. Technical article bodies remain English under the existing disclosure.
