# API contracts

The frontend talks only to the FastAPI backend through `src/services/api/*.api.js`
and `request()` in `src/services/http.js`, which throws a normalized
`ServiceError`. JSDoc shapes live in `src/services/contracts.js`. The live,
authoritative schema is `GET /api/openapi.json`.

All authenticated routes take `Authorization: Bearer <session token>`. There is
no API-key or third-party-token login (W8).

## 1. Access model

- Access is granted by a platform administrator. There are no plans for sale, no
  trial and no checkout.
- A new workspace is **pending**: every feature flag is off until a grant.
- Grantable flags: `discover`, `swipe_files` (boards and share links),
  `monitors`, `team_accounts`.
- Credit and daily limits are enforced server-side by `assert_can_spend`.

| Status | `detail.code` | Meaning |
|---|---|---|
| 403 | `feature_disabled` | The workspace has no grant for that feature |
| 402 | `insufficient_credits` | Not enough credits; ask a workspace administrator |
| 429 | `daily_limit_reached` | Daily credit limit reached; resets 00:00 UTC |
| 429 | `rate_limited` | Too many requests from this client |
| 503 | `auth_rate_limiter_unavailable` | Auth limiter fault; auth fails closed |

## 2. Auth — `/api/auth`

| Method | Path | Notes |
|---|---|---|
| POST | `/sign-up` | Always `202 {"ok": true, "message": ...}`, no token, whether or not the email was registered. The client signs in next. Password 8–128 chars. |
| POST | `/sign-in` | Session response with `access_token`; wrong email or password is the same generic `401`. |
| GET | `/session` | Current user, workspace, `access_status`, effective `feature_flags`, credit fields. |
| POST | `/sign-out` (`/logout`) | Revokes all sessions for the user server-side. |
| POST | `/forgot-password`, `/reset-password` | Same public response for any email; single-use 30-minute token. |
| POST | `/session/onboarding/complete`, `/session/onboarding/restart` | Onboarding tour state. |

## 3. Discover — `/api/discovery` (flag `discover`)

| Method | Path | Notes |
|---|---|---|
| POST | `/jobs` | Start a search (`query`, `filters`, `query_language`). Runs through the durable `work_items` outbox and the jobs worker. |
| GET | `/jobs` | Recent jobs. |
| GET | `/jobs/{job_id}` | Status, stage, deadline, `failure_kind`. |
| POST | `/jobs/{job_id}/cancel` | Tenant-checked cancellation. |
| GET | `/jobs/{job_id}/results` | Paginated creatives. `sort` = `days_active_desc` (default), `first_seen_desc`, `composite_desc`, `hook_desc`, `impressions_desc`; anything else is `422`. Nulls sort last. Optional view filters on stored rows: `min_days` ∈ {30, 60, 90} (ads with an unknown run length are excluded and counted in `hidden_unknown_run_length`, never treated as 0) and `min_score` 0–10 (text-rubric minimum); other values are `422`. |

Scores (`hook`, `clarity`, `retention`, `composite`) are a **text rubric on a
0–10 scale**, not measured performance. `metrics.impressions_est` is the upper
bound of the range Meta's official Ad Library API reports and is `null` for
every other source; spend, CTR and engagement are `null` unless Meta reports them.

## 4. Creatives and boards

| Method | Path | Flag | Notes |
|---|---|---|---|
| GET | `/api/creatives/{id}` | `discover` | Creative detail (tenant-scoped through its job). |
| GET | `/api/creatives/saved` | `discover` + `swipe_files` | Saved creatives (boards). |
| POST / DELETE | `/api/creatives/{id}/save` | `discover` + `swipe_files` | Save to / remove from a board. |
| POST | `/api/creatives/custom` | `discover` + `swipe_files` | Add a custom reference to a board. |
| GET / POST | `/api/playbooks` | `swipe_files` | List / create a shareable board report. |
| GET | `/api/playbooks/public/{public_id}` | signed-in owner org | Read a shared report. |

## 5. Monitors — `/api/monitors` (flag `monitors`)

CRUD on saved competitor watches, `POST /{id}/run`, `GET /events`, and
`POST /tick` for the scheduler (requires `X-Cron-Secret`; `503` while
`CRON_SECRET` is unset). See DEVELOPMENT.md → Monitors.

## 6. Account, team, support, notifications

- `/api/account`: `profile` (GET/PATCH), `avatar`, `access`, `access-requests`,
  `access-grants`, `usage/today`, `workspace`, `onboarding-complete`, and team
  invites/members (`team_accounts`, flag-hidden in the UI).
- `/api/support/tickets`, `/api/notifications`, `/api/updates` (banner and
  public updates).

## 7. Admin — `/api/admin`

Platform-admin only: access requests (approve/reject), organization access
grant/revoke and flags, credit grants, users (role, status, ban, impersonate),
support tickets, usage, system health, plans, broadcast and updates.

## 8. Frontend request cancellation

`discoverService` calls accept a final `{ signal: AbortSignal }`.
`useDiscoverySearch` owns a controller per submission and per refinement;
unmount, navigation, cancel or resubmission aborts outstanding fetches and
retry waits and fences stale state updates. Aborting a client request is
**not** proof that the backend job stopped: only `POST /jobs/{id}/cancel` asks
the server to stop. Requests keep their bounded transport deadline and the hook
keeps its overall job deadline.
