# Helix security audit (W9)

Scope: every API route in `backend/app` (116 method and path pairs, listed from the
running FastAPI app object), plus CORS, the frontend bundle, source maps, error
responses and security headers. Branch `fix/w9-security-guardrails`. Each claim
cites code. "Verified" names the test in this PR or the live check.

## Summary

| ID | Sev | Finding | Status |
|---|---|---|---|
| A1 | **P0** | Per-IP limits trust the client IP, so how it is derived matters. A live test on 2026-11-11 (30 guest-link lookups returned 429, then 5 more with forged `X-Forwarded-For` all went through) hit the deploy that predates PR #37, so it does not prove the current code is bypassable. If uvicorn trusts every hop (`*`), it takes the left-most `X-Forwarded-For` value, which the client controls. | Fixed in code: `render.yaml:19` runs uvicorn with `--proxy-headers --forwarded-allow-ips 10.0.0.0/8`. uvicorn then trusts only Render's proxy and uses the right-most untrusted `X-Forwarded-For` entry (the one Render appended), and #37's limiter (`app/middleware/rate_limit.py` `client_ip`) uses that address. `--no-proxy-headers` was rejected: every request would look like the proxy and share one bucket. Tests: two real clients get separate buckets, and a forged left-most entry gets no new bucket (`test_w9_security_guardrails.py`). **The Render dashboard start command must match `render.yaml`.** The per-email and per-account limits (A2) hold whatever the IP. |
| A2 | **P0** | Limits were only per IP. Sign-up, forgot-password, Discover search and monitor runs had no per-account or per-email limit, so with A1 they were effectively unlimited. | Fixed: `app/core/limits.py`, used in `app/api/routers/auth.py` (sign-up, sign-in, forgot, reset), and `app/core/deps.py` `account_rate_limit` on `POST /api/discovery/jobs`, `POST /api/monitors` and `POST /api/monitors/{id}/run`. An account write limit covers support tickets and replies, access requests, team invites, share links, drafts and avatar uploads. Tests: `backend/tests/test_w9_security_guardrails.py`. |
| A3 | **P0** | Metapi had only a global monthly record budget (`METAPI_MONTHLY_RECORD_BUDGET`, 3,000) and daily search counts. One workspace, or many 7-day trial workspaces, could use the whole month. | Fixed. Per-workspace monthly record cap (default 150; plan `limits.records_per_month`, editable in Admin → Pricing). Global safety stop (`METAPI_GLOBAL_SAFETY_STOP`, default 2,500). Per-task record clamp (`METAPI_MAX_RECORDS_PER_TASK`). All are checked before the Metapi request (`app/services/provider_budget.py` `reserve_provider_records`, `app/services/scraping/metapi_provider.py` `_run_task`) and before a search is queued (`app/services/discover_service.py`, 429 `workspace_record_budget_reached` / `platform_record_budget_reached`). Counts are stored in Postgres (`workspace_daily_usage.records`, migration `f2b4d6e8a0c3`). Access & Usage shows the stored count. |
| A4 | P1 | Monitors could run `every_6h` (`app/services/monitor_service.py` `CADENCE_INTERVALS`): 4 paid runs a day per monitor. | Fixed: `MONITOR_MIN_INTERVAL_HOURS` (default 12) refuses faster cadences (422 `cadence_below_floor`), and the scheduler never runs faster, even for monitors saved earlier (`_interval`). |
| A5 | P1 | Sign-up is auto-accepted with a 7-day trial (`app/services/auth_service.py:216` `_start_signup_trial`) and there is no email verification, so trials can be farmed with throwaway addresses. | Mitigated, not fixed: global sign-up ceiling (40/h), per-workspace record cap, global safety stop. **Follow-up:** require a verified email before the trial turns on Discover. There is no verification or resend-verification endpoint today. |
| A6 | P2 | `/docs`, `/redoc` and `/api/openapi.json` were public in production (FastAPI defaults), publishing every route and parameter. | Fixed: off when `ENVIRONMENT=production` (`app/main.py`). |
| A7 | P2 | The new limits are in process (one Render instance). They reset on restart and won't be shared if a second instance is added. | Accepted on the free plan; the money caps are in Postgres. Revisit before scaling out. |
| A8 | P2 | CORS allows all methods and headers with credentials (`app/main.py` CORS block). Origins are an explicit list plus a validated regex (`app/core/config.py`: `BACKEND_CORS_ORIGIN_REGEX` must be `^https://…` ending in an escaped domain). Sessions are bearer tokens in localStorage, not cookies, so this isn't exploitable today. | Follow-up: narrow the methods and headers. |
| A9 | P2 | No Content-Security-Policy on API responses. `app/main.py` sets nosniff, `X-Frame-Options: DENY`, HSTS, Referrer-Policy and Permissions-Policy. The app's own CSP comes from Vercel. | Follow-up: add `default-src 'none'` to API responses and check the Vercel headers. |

## Checked and found safe (with evidence)

- **RLS**: all 40 tenant tables have RLS on with policies, and the app roles have no `BYPASSRLS` or superuser (read-only catalog query on the production branch, 2026-11-11). Request sessions are bound to the user's workspaces in `app/core/deps.py:238` `_bind_request_tenant`. Worker-only access needs `helix.worker_claim` (`app/core/tenancy.py:108`). Since migration `e1a3c5e7f9b2`, app roles have read-only access to the shared tables the app never writes.
- **Ownership**: monitors load with `org_id` in the WHERE clause (`app/services/monitor_service.py` `_load_owned`). Discover job reads are scoped by `get_user_org_ids` (`app/api/routers/discover.py`).
- **Guest share links** are HMAC-signed tokens bound to one workspace and an expiry (`app/services/board_share_service.py:62` `sign_token`, `:69` `verify_token`, capped at 512 characters), so guessing isn't practical. They stop working when the creator is suspended or banned (W8).
- **Admin routes**: admin routes that change data require `get_current_full_admin`; read routes require `get_current_admin` (`app/core/deps.py:135`, `:146`). Impersonation refuses admin targets and the caller themself (`app/api/routers/admin.py:167`).
- **Suspended users** are refused on every authenticated request (`app/core/deps.py:105`, 403 `user_suspended`).
- **Monitor tick** refuses every request unless `CRON_SECRET` is set and matches, compared with `hmac.compare_digest` (`app/api/routers/monitors.py` `tick`).
- **Health diagnostic key**: whether provider keys are present is shown only with a matching `X-Admin-Secret`, compared in constant time, and never when the key equals `SECRET_KEY` (`app/api/routers/health.py` `health_check`). Only true/false values are returned, never the keys.
- **Uploads**: bare filenames only, the path is checked against the upload folder, and access is checked by signature or session (`app/api/routers/uploads.py:90`).
- **Avatar upload** has a size cap enforced while the file streams in (`app/api/routers/account.py`, `MAX_AVATAR_BYTES`).
- **Error responses**: FastAPI runs without `debug`, so unhandled errors return a plain 500 with no traceback. Handlers log through `log_event` without payloads or tracebacks (`app/core/observability.py:23`).
- **Frontend bundle**: the only build-time variables read are `VITE_ANALYTICS_DOMAIN`, `VITE_ANALYTICS_SCRIPT`, `VITE_ENABLE_EXPERIMENTAL_FEATURES` and `VITE_SUPPORT_EMAIL` (search for `import.meta.env` in `src/`). No secret is in the bundle, and CI runs a secret scan.
- **Source maps**: the `build` section of `vite.config.js` doesn't enable `sourcemap`, and Vite's default is off, so production builds have none.
- **MCP endpoints**: the backend exposes none; there are no MCP routes in the table below.

## Rate-limit design

| Layer | Key | Where | Store | Why |
|---|---|---|---|---|
| Per IP | client IP (Render proxy trusted) | `app/middleware/rate_limit.py` | process memory | cheap first line; only as good as the client IP (A1) |
| Per email / global | email (hashed) or route name | `app/core/limits.py`, `app/api/routers/auth.py` | process memory | a forged IP can't reset it; no database write on every auth request |
| Per account | user id | `app/core/deps.py` `account_rate_limit` | process memory | same reason |
| Sign-in lock | account | `app/services/auth_service.py` | Postgres (`users.signup_metadata`) | survives restarts |
| Metapi records | workspace per month, global per month | `app/services/provider_budget.py` | Postgres | money: must survive restarts and be exact |

Every limit answers **429** with `Retry-After` and a `detail.code` (`rate_limited`, `daily_search_cap_reached`, `workspace_record_budget_reached`, `platform_record_budget_reached`). The frontend shows each in English and Arabic (`src/features/auth/authFailure.js`, `src/i18n/w5AuthDocs.js`, `src/i18n/w8Product.js`, `src/pages/DiscoverPage.jsx`).

## New Render settings (all optional; defaults shown)

`METAPI_WORKSPACE_MONTHLY_RECORDS=150`, `METAPI_GLOBAL_SAFETY_STOP=2500`, `METAPI_MAX_RECORDS_PER_TASK=30`, `MONITOR_MIN_INTERVAL_HOURS=12`, `AUTH_EMAIL_LIMIT=5`, `AUTH_EMAIL_WINDOW_S=900`, `SIGN_IN_EMAIL_LIMIT=20`, `SIGN_UP_GLOBAL_LIMIT=40`, `SIGN_UP_GLOBAL_WINDOW_S=3600`, `RESET_GLOBAL_LIMIT=60`, `ACCOUNT_SEARCH_LIMIT=5`, `ACCOUNT_SEARCH_WINDOW_S=300`, `ACCOUNT_MONITOR_LIMIT=5`, `ACCOUNT_MONITOR_WINDOW_S=300`, `ACCOUNT_WRITE_LIMIT=30`, `ACCOUNT_WRITE_WINDOW_S=3600`.

Start command (Render dashboard → Settings → Start Command): `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips 10.0.0.0/8`

## Route table

Auth: *user* = `get_current_user` (session token; suspended users refused). *+ feature flag* = `require_feature`. *admin* / *full admin* = platform admin checks. The rate limits are the ones in place after this PR. Every *user* route runs inside the caller's RLS scope.

| Method | Path | Handler | Auth | Rate limit (after this PR) | Paid resource |
|---|---|---|---|---|---|
| POST | `/api/auth/sign-up` | `app/api/routers/auth.py:132` | none | IP 30/min; email 5/15 min; global 40/h | Resend email |
| POST | `/api/auth/sign-in` | `app/api/routers/auth.py:159` | none | IP 30/min; email 20/15 min; account lock 10 fails/15 min | — |
| POST | `/api/auth/logout` | `app/api/routers/auth.py:177` | none | — | — |
| POST | `/api/auth/sign-out` | `app/api/routers/auth.py:177` | none | — | — |
| POST | `/api/auth/forgot-password` | `app/api/routers/auth.py:207` | none | IP 30/min; email 5/15 min | Resend email |
| POST | `/api/auth/reset-password` | `app/api/routers/auth.py:250` | none | IP 30/min; global 60/15 min | — |
| GET | `/api/auth/session` | `app/api/routers/auth.py:268` | user | — | — |
| POST | `/api/auth/session/onboarding/complete` | `app/api/routers/auth.py:272` | user | — | — |
| POST | `/api/auth/session/onboarding/restart` | `app/api/routers/auth.py:279` | user | — | — |
| GET | `/api/account/profile` | `app/api/routers/account.py:85` | user | — | — |
| PATCH | `/api/account/profile` | `app/api/routers/account.py:97` | user | — | — |
| POST | `/api/account/avatar` | `app/api/routers/account.py:156` | user | account 30/h | — |
| GET | `/api/account/usage/today` | `app/api/routers/account.py:185` | user | — | — |
| POST | `/api/account/onboarding-complete` | `app/api/routers/account.py:233` | user | — | — |
| GET | `/api/account/access` | `app/api/routers/account.py:242` | user | — | — |
| POST | `/api/account/access-requests` | `app/api/routers/account.py:254` | user | IP 10/min; account 30/h | — |
| POST | `/api/account/access-grants` | `app/api/routers/account.py:272` | user | — | — |
| POST | `/api/account/workspace` | `app/api/routers/account.py:285` | user | — | — |
| GET | `/api/account/billing` | `app/api/routers/account.py:314` | user | — | — |
| POST | `/api/account/billing/provider-events` | `app/api/routers/account.py:322` | user | — | — |
| GET | `/api/account/team` | `app/api/routers/account.py:333` | user | — | — |
| POST | `/api/account/team/invites` | `app/api/routers/account.py:340` | user | account 30/h | Resend email |
| DELETE | `/api/account/team/invites/{invite_id}` | `app/api/routers/account.py:348` | user | — | — |
| POST | `/api/account/team/invites/accept` | `app/api/routers/account.py:356` | user | — | — |
| DELETE | `/api/account/team/members/{member_id}` | `app/api/routers/account.py:364` | user | — | — |
| GET | `/api/notifications` | `app/api/routers/notifications.py:9` | user | — | — |
| POST | `/api/notifications/{notification_id}/read` | `app/api/routers/notifications.py:17` | user | — | — |
| POST | `/api/notifications/read-all` | `app/api/routers/notifications.py:25` | user | — | — |
| POST | `/api/discovery/jobs` | `app/api/routers/discover.py:13` | user + feature flag | IP 20/min (paid bucket); account 5/5 min; daily searches; monthly records | Metapi records, AI |
| GET | `/api/discovery/jobs/{job_id}` | `app/api/routers/discover.py:28` | user + feature flag | — | — |
| POST | `/api/discovery/jobs/{job_id}/cancel` | `app/api/routers/discover.py:34` | user + feature flag | — | — |
| GET | `/api/discovery/jobs/{job_id}/results` | `app/api/routers/discover.py:57` | user + feature flag | — | — |
| GET | `/api/discovery/jobs/{job_id}/results.md` | `app/api/routers/discover.py:72` | user + feature flag | — | — |
| GET | `/api/discovery/stored-results` | `app/api/routers/discover.py:86` | user + feature flag | — | — |
| GET | `/api/discovery/jobs` | `app/api/routers/discover.py:122` | user + feature flag | — | — |
| GET | `/api/discovery/drafts` | `app/api/routers/discover.py:151` | user + feature flag | — | — |
| POST | `/api/discovery/drafts` | `app/api/routers/discover.py:156` | user + feature flag | IP 10/min; account 30/h | — |
| DELETE | `/api/discovery/drafts/{draft_id}` | `app/api/routers/discover.py:167` | user + feature flag | — | — |
| GET | `/api/creatives` | `app/api/routers/creatives.py:13` | user + feature flag | — | — |
| GET | `/api/creatives/saved` | `app/api/routers/creatives.py:27` | user + feature flag | — | — |
| POST | `/api/creatives/custom` | `app/api/routers/creatives.py:37` | user + feature flag | IP 20/min (paid bucket) | AI provider |
| POST | `/api/creatives/{creative_id}/save` | `app/api/routers/creatives.py:45` | user + feature flag | IP 20/min (paid bucket) | — |
| DELETE | `/api/creatives/{creative_id}/save` | `app/api/routers/creatives.py:54` | user + feature flag | IP 20/min (paid bucket) | — |
| GET | `/api/creatives/{creative_id}` | `app/api/routers/creatives.py:63` | user + feature flag | — | — |
| GET | `/api/updates` | `app/api/routers/updates.py:31` | optional | — | — |
| GET | `/api/updates/banner` | `app/api/routers/updates.py:54` | optional | — | — |
| GET | `/api/updates/admin/all` | `app/api/routers/updates.py:84` | full admin | — | — |
| POST | `/api/updates/admin` | `app/api/routers/updates.py:97` | full admin | — | — |
| GET | `/api/updates/admin/{update_id}` | `app/api/routers/updates.py:133` | full admin | — | — |
| POST | `/api/updates/admin/{update_id}` | `app/api/routers/updates.py:149` | full admin | — | — |
| PUT | `/api/updates/admin/{update_id}` | `app/api/routers/updates.py:149` | full admin | — | — |
| PATCH | `/api/updates/admin/{update_id}` | `app/api/routers/updates.py:149` | full admin | — | — |
| DELETE | `/api/updates/admin/{update_id}` | `app/api/routers/updates.py:188` | full admin | — | — |
| GET | `/api/admin/overview/stats` | `app/api/routers/admin.py:24` | admin | — | — |
| GET | `/api/admin/jobs` | `app/api/routers/admin.py:28` | admin | — | — |
| GET | `/api/admin/system/health` | `app/api/routers/admin.py:32` | admin | — | — |
| GET | `/api/admin/plans` | `app/api/routers/admin.py:37` | admin | — | — |
| POST | `/api/admin/plans` | `app/api/routers/admin.py:41` | full admin | — | — |
| PUT | `/api/admin/plans/{plan_id}` | `app/api/routers/admin.py:49` | full admin | — | — |
| DELETE | `/api/admin/plans/{plan_id}` | `app/api/routers/admin.py:58` | full admin | — | — |
| GET | `/api/admin/organizations` | `app/api/routers/admin.py:67` | admin | — | — |
| POST | `/api/admin/organizations/{org_id}/grant-credits` | `app/api/routers/admin.py:71` | full admin | — | — |
| POST | `/api/admin/organizations/{org_id}/switch-plan` | `app/api/routers/admin.py:80` | full admin | — | — |
| POST | `/api/admin/organizations/{org_id}/feature-flags` | `app/api/routers/admin.py:89` | full admin | — | — |
| GET | `/api/admin/usage` | `app/api/routers/admin.py:99` | admin | — | — |
| GET | `/api/admin/usage/logs` | `app/api/routers/admin.py:103` | admin | — | — |
| GET | `/api/admin/users` | `app/api/routers/admin.py:125` | admin | — | — |
| POST | `/api/admin/users/{user_id}/status` | `app/api/routers/admin.py:129` | full admin | — | — |
| POST | `/api/admin/users/{user_id}/ban` | `app/api/routers/admin.py:138` | full admin | — | — |
| POST | `/api/admin/users/{user_id}/role` | `app/api/routers/admin.py:147` | full admin | — | — |
| POST | `/api/admin/users/{user_id}/plan` | `app/api/routers/admin.py:158` | full admin | — | — |
| POST | `/api/admin/users/{user_id}/impersonate` | `app/api/routers/admin.py:167` | full admin | — | — |
| POST | `/api/admin/broadcast` | `app/api/routers/admin.py:187` | full admin | — | Resend email |
| GET | `/api/admin/support/tickets` | `app/api/routers/admin.py:202` | admin | — | — |
| POST | `/api/admin/support/tickets/{ticket_id}/reply` | `app/api/routers/admin.py:216` | admin | — | Resend email |
| PATCH | `/api/admin/support/tickets/{ticket_id}/status` | `app/api/routers/admin.py:228` | admin | — | — |
| GET | `/api/admin/access-requests` | `app/api/routers/admin.py:251` | full admin | — | — |
| POST | `/api/admin/access-requests/{request_id}/approve` | `app/api/routers/admin.py:261` | full admin | — | — |
| POST | `/api/admin/access-requests/{request_id}/reject` | `app/api/routers/admin.py:273` | full admin | — | — |
| POST | `/api/admin/organizations/{org_id}/access-grant` | `app/api/routers/admin.py:283` | full admin | — | — |
| POST | `/api/admin/organizations/{org_id}/access-revoke` | `app/api/routers/admin.py:295` | full admin | — | — |
| POST | `/api/support/tickets` | `app/api/routers/support.py:36` | user | IP 10/min; account 30/h | Resend email |
| GET | `/api/support/tickets` | `app/api/routers/support.py:59` | user | — | — |
| GET | `/api/support/tickets/{ticket_id}` | `app/api/routers/support.py:66` | user | — | — |
| POST | `/api/support/tickets/{ticket_id}/reply` | `app/api/routers/support.py:74` | user | IP 10/min; account 30/h | Resend email |
| POST | `/api/playbooks` | `app/api/routers/playbooks.py:22` | user + feature flag | IP 20/min (paid bucket) | AI provider |
| GET | `/api/playbooks` | `app/api/routers/playbooks.py:49` | user + feature flag | — | — |
| GET | `/api/playbooks/public/{public_id}` | `app/api/routers/playbooks.py:56` | user + feature flag | — | — |
| GET | `/api/health/live` | `app/api/routers/health.py:18` | none | — | — |
| GET | `/api/health/ready` | `app/api/routers/health.py:24` | none | — | — |
| GET | `/api/health` | `app/api/routers/health.py:53` | none (X-Admin-Secret for detail) | — | — |
| GET | `/api/monitors` | `app/api/routers/monitors.py:44` | user + feature flag | — | — |
| POST | `/api/monitors` | `app/api/routers/monitors.py:53` | user + feature flag | IP 20/min (paid bucket); account 5/5 min; cadence floor | Metapi records |
| GET | `/api/monitors/events` | `app/api/routers/monitors.py:73` | user + feature flag | — | — |
| GET | `/api/monitors/events.md` | `app/api/routers/monitors.py:89` | user + feature flag | — | — |
| PATCH | `/api/monitors/{monitor_id}` | `app/api/routers/monitors.py:102` | user + feature flag | IP 20/min (paid bucket) | — |
| DELETE | `/api/monitors/{monitor_id}` | `app/api/routers/monitors.py:114` | user + feature flag | IP 20/min (paid bucket) | — |
| POST | `/api/monitors/{monitor_id}/run` | `app/api/routers/monitors.py:123` | user + feature flag | IP 20/min (paid bucket); account 5/5 min; cadence floor | Metapi records |
| POST | `/api/monitors/tick` | `app/api/routers/monitors.py:132` | X-Cron-Secret | — | Metapi records |
| GET | `/api/boards` | `app/api/routers/boards.py:22` | user + feature flag | — | — |
| GET | `/api/boards/items` | `app/api/routers/boards.py:30` | user + feature flag | — | — |
| POST | `/api/boards/share-links` | `app/api/routers/boards.py:45` | user + feature flag | IP 10/min; account 30/h | — |
| GET | `/api/boards/share-links` | `app/api/routers/boards.py:54` | user + feature flag | — | — |
| DELETE | `/api/boards/share-links/{link_id}` | `app/api/routers/boards.py:63` | user + feature flag | — | — |
| GET | `/api/boards/team` | `app/api/routers/boards.py:76` | user + feature flag | — | — |
| GET | `/api/boards/team/items` | `app/api/routers/boards.py:84` | user + feature flag | — | — |
| GET | `/api/archive` | `app/api/routers/archive.py:14` | user + feature flag | — | — |
| GET | `/api/archive/by-creative/{creative_id}` | `app/api/routers/archive.py:25` | user + feature flag | — | — |
| GET | `/api/public/boards/{token}` | `app/api/routers/boards.py:94` | signed share token | IP 30/min | — |
| GET | `/api/public/pricing` | `app/api/routers/pricing.py:12` | none | — | — |
| GET | `/uploads/{filename}` | `app/api/routers/uploads.py:90` | signed URL / session | — | — |
| GET | `/health` | `app/main.py:133` | none (X-Admin-Secret for detail) | — | — |
| GET | `/api` | `app/main.py:133` | none | — | — |
| GET | `/` | `app/main.py:133` | none | — | — |
