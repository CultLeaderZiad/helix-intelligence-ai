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
| 429 | `too_many_sign_in_attempts` | Sign-in for this email is locked after repeated wrong passwords (`Retry-After` set). Unknown emails get the same answer on the same attempt. A password reset ends the lock |
| 503 | `auth_rate_limiter_unavailable` | Auth limiter fault; auth fails closed |
| 503 | `discover_paused` | `DISCOVER_ENABLED=false`: new searches and monitor runs are refused; no credit is used |
| 422 | `query_too_long` | Discover search text over 300 characters |
| 429 | `daily_search_cap_reached` | The workspace started `DISCOVER_MAX_SEARCHES_PER_WORKSPACE_PER_DAY` searches today (cache hits and refunds do not change the count) |

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
| POST | `/jobs` | Start a search (`query`, `filters`, `query_language`). Runs through the durable `work_items` outbox and the jobs worker. `query` may be a brand or domain, a niche, a Facebook page id, or an Ad Library page link (`view_all_page_id`). With Metapi, a brand query first finds the advertiser page whose name is the brand (an exact-phrase keyword task of `METAPI_RESOLVE_COUNT` ads, default 30) and then loads that page's own ads (a second task, which reserves its own slot under the daily provider cap); those ads skip the keyword relevance filter. If no page name matches, the keyword results are filtered as before. |
| GET | `/jobs` | Recent jobs, newest first; each row includes its `query`, so clients build search history from the server. |
| GET | `/drafts` | The caller's saved search drafts in the active workspace (`{items: [{id, title, query, notes, filters, created_at}]}`), newest first, at most 50. |
| POST | `/drafts` | Save a draft (`title`, `query` required, `notes`, `filters`). Only `country`, `min_days_active`, `min_score` are kept from `filters`. `201`; empty query `422`; over 50 drafts `409`. |
| DELETE | `/drafts/{id}` | Delete one of the caller's own drafts; anyone else's is `404`. |
| GET | `/jobs/{job_id}` | Status, stage, deadline, `failure_kind`. A job stopped by the global hard stop fails with `failure_kind` `discover_paused` or `provider_budget` and its credit is refunded. |
| POST | `/jobs/{job_id}/cancel` | Tenant-checked cancellation. |
| GET | `/stored-results?query=&max_age_days=` | W9-1. Latest finished search for `query` in the caller's workspace (JSON or Markdown). Never starts a search; 0 credits, 0 Metapi records. `max_age_days` > 0 only considers searches within that many days that found ads (the UI uses 7 to offer "View stored results (0 records)" before a paid run). JSON adds `job_id`, `searched_at`, `records_used: 0`. `404` if none. |
| GET | `/jobs/{job_id}/results` | Paginated creatives. `sort` = `days_active_desc` (default), `first_seen_desc`, `composite_desc`, `hook_desc`, `impressions_desc`; anything else is `422`. Nulls sort last. Optional view filters on stored rows: `min_days` ∈ {30, 60, 90} (ads with an unknown run length are excluded and counted in `hidden_unknown_run_length`, never treated as 0) and `min_score` 0–10 (text-rubric minimum); other values are `422`. |

Scores (`hook`, `clarity`, `retention`, `composite`) are a **text rubric on a
0–10 scale**, not measured performance. `metrics.impressions_est` is the upper
bound of the range Meta's official Ad Library API reports and is `null` for
every other source; spend, CTR and engagement are `null` unless Meta reports them.

## 4. Creatives and boards

| Method | Path | Flag | Notes |
|---|---|---|---|
| GET | `/api/creatives/{id}` | `discover` | Creative detail (tenant-scoped through its job). W9-2: every creative payload adds `page_id` (the advertiser's Facebook page id, digits only, or `null`). |
| GET | `/api/creatives/saved` | `discover` + `swipe_files` | Saved creatives (boards). W9-1: optional `q` runs the same full-text search as `/api/archive/search`, ranked by match. W9-2: `q` also matches a saved ad whose tag equals `q` or whose notes match it (FTS, `simple` + `arabic`); optional `tag` keeps only ads with that tag. Each item adds `tags: string[]` and `notes: [{id, body, author_id, created_at, updated_at}]`. |
| POST / DELETE | `/api/creatives/{id}/save` | `discover` + `swipe_files` | Save to / remove from a board. |
| POST | `/api/creatives/custom` | `discover` + `swipe_files` | Add a custom reference to a board. |
| GET / POST | `/api/playbooks` | `swipe_files` | List / create a shareable board report. |
| GET | `/api/playbooks/public/{public_id}` | signed-in owner org | Read a shared report. |
| GET | `/api/boards` | `swipe_files` | The caller's boards (saved-ad collections) with counts. |
| GET / POST | `/api/boards/share-links` | `swipe_files` | List / create guest links. Body `{collection, expires_in_days ∈ {1, 7, 30}}`; at most 5 active links per board (`409`). |
| DELETE | `/api/boards/share-links/{id}` | `swipe_files` | Revoke (creator only; sets `revoked_at`, nothing is deleted). |
| GET | `/api/boards/tags` | `swipe_files` | W9-2. The caller's tags with counts: `{items: [{tag, count}]}` (most used first, at most 200). |
| PUT | `/api/boards/saved/{creative_id}/tags` | `swipe_files` | W9-2. Replace the tags on one of the caller's saved ads. Body `{tags: string[]}`; tags are trimmed, whitespace-collapsed, lower-cased, at most 40 chars, de-duplicated, at most 20 per ad (`422 too_many_tags`). Returns `{creative_id, tags}`. `404 not_saved` if the caller has not saved it. |
| POST | `/api/boards/saved/{creative_id}/notes` | `swipe_files` | W9-2. Add a note `{body}` (1–2000 chars, at most 50 per ad). `201` with the note. |
| PATCH / DELETE | `/api/boards/saved/{creative_id}/notes/{note_id}` | `swipe_files` | W9-2. Edit (`{body}`, sets `updated_at`) or delete a note. Author only; anyone else gets `404 note_not_found`. |
| GET | `/api/boards/team` | `swipe_files` + `team_accounts` | Boards saved by current members (owner + `organization_members`) of the active workspace, with owner display name. Former members' boards are not listed. |
| GET | `/api/boards/team/items?owner_id=&collection=` | `swipe_files` + `team_accounts` | Read-only items of one teammate's board (`404` for non-members or other workspaces). Writes stay with the owner. |
| GET | `/api/public/boards/{token}` | none (token is the capability) | Read-only board view. Token = base64url `{l, o, e}` + HMAC-SHA256 with a key derived from `SECRET_KEY`. The MAC and expiry are checked before any query; RLS is then bound to the token's workspace only, and the link row must be unrevoked with the same expiry. Any failure is `404`. `Cache-Control: no-store`, `X-Robots-Tag: noindex`. Display fields only; `impressions_est` only for Meta-official rows; `days_active` stays `null` when unknown. Rotating `SECRET_KEY` invalidates every guest link. |

### Permanent ad archive — `/api/archive` (flag `discover`)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/archive` | Paginated archive entries for the caller's workspace (`brand` filter optional). Includes `cap_per_workspace`. |
| GET | `/api/archive/search?q=&scope=&page=&page_size=` | W9-1. Postgres full-text search over the workspace archive and the caller's saved ads (brand, headline, body, CTA, landing domain), with the `simple` and `arabic` configs OR-ed, so English, Arabic and mixed text match. `q` is free text (`websearch_to_tsquery`: quotes, `-word`), trimmed to 200 chars; empty `422`. `scope` = `all` (default), `archive`, `saved`; other `422`. Response `{query, scope, page, page_size, records_used: 0, archive: {items, total, has_more}, saved: {items, total, has_more} | null}`. `saved` is `null` under `all` when the plan lacks `swipe_files`; `scope=saved` then returns `403`. Archive rows are limited to the caller's workspaces (and RLS); saved rows to the caller. GIN indexes `ix_ad_archive_fts`, `ix_creatives_fts`. |
| GET | `/api/archive/by-creative/{creative_id}` | The archived copy of one creative, or `404` until the background copy exists. |

After a Discover search succeeds with results, an `archive` work item copies
every ad into `ad_archive`: text always; media only over https from Meta CDN
hosts (`ARCHIVE_MEDIA_HOST_SUFFIXES`, default `fbcdn.net, fbsbx.com,
cdninstagram.com, facebook.com`) through `safe_fetch`, up to
`ARCHIVE_MAX_MEDIA_BYTES` (default 15 MB) per file. Media goes to private R2
when `R2_*` is configured, else the guarded `/uploads` directory, and is read
back through short-lived signed URLs. `media_status` is one of `stored`,
`too_large`, `not_allowed`, `failed`, `none`.

**Per-workspace cap:** `ARCHIVE_MAX_ENTRIES_PER_ORG` (default 5000). Past the
cap new ads are not archived (logged as `ad archive cap reached`); existing
entries keep being refreshed. Entries are keyed by Ad Library id (or a text
hash) per workspace, so re-running a search does not duplicate them.
`ARCHIVE_ENABLED=false` turns the copy off.

## 5. Monitors — `/api/monitors` (flag `monitors`)

CRUD on saved competitor watches, `POST /{id}/run`, `GET /events`, and
`POST /tick` for the scheduler (requires `X-Cron-Secret`; `503` while
`CRON_SECRET` is unset). See DEVELOPMENT.md → Monitors.

### Monitor this brand (W9-2)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/monitors/brand/preview?page_id=&brand_name=&cadence=` | The monitor one click would create, read only (0 credits, 0 records): `{query, name, watch: "page_id" \| "brand_name", cadence, records_per_run, records_per_month, records_remaining, records_cap, fits_this_month, existing_monitor_id}`. A page id (or an Ad Library link with `view_all_page_id`) is preferred, so runs read that advertiser directly; otherwise the brand name. Neither: `422 brand_required`. `cadence` defaults to `weekly`. |
| POST | `/api/monitors/brand` | Body `{page_id?, brand_name?, cadence?, notify_in_app?, notify_email?}`. Creates the monitor through the same path as `POST /api/monitors`: plan limits, the W9-1 record check (`429 workspace_record_cap_reached`) and the duplicate check (`409`). `201` with the monitor. |

### Continuous runs and the daily digest

The jobs worker ticks the monitor scheduler every
`MONITOR_SCHEDULER_INTERVAL_S` (default 300; `0` disables it), so monitors
run without an external cron. `POST /api/monitors/tick` with
`X-Cron-Secret` still works; the claim is `FOR UPDATE SKIP LOCKED`, so both
can run. After a run with changes, the owner gets at most one digest per
`MONITOR_DIGEST_INTERVAL_H` (default 24) per workspace that rolls up every
monitor's new / copy-changed / stopped ads since the last digest: always as
an in-app notification (`type = monitor_digest`), and by email only when
Resend is configured and email is on for at least one of those monitors.

### Agent surface (read-only Markdown + MCP)

Markdown (`text/markdown; charset=utf-8`, `Vary: Accept`) is returned when
the request sends `Accept: text/markdown`, adds `?format=md`, or uses the
`.md` form: `GET /api/discovery/jobs/{id}/results(.md)`,
`GET /api/discovery/stored-results?query=` (latest finished search for that
query in the caller's workspace; never starts a search; `404` if none),
`GET /api/creatives/{id}(.md)`, `GET /api/boards/items?collection=`
(caller's own board; JSON or Markdown), `GET /api/monitors/events(.md)`,
`GET /api/public/boards/{token}(.md)`. Labels match the UI: run length
`unknown` when null, text rubric (not a prediction), reach only for
Meta-official rows. The read-only MCP server in `agents/mcp` (tools
`search_ads`, `get_board`, `list_monitor_changes`, `get_ad`) calls only these
GET routes with the user's own session token. No API keys exist; the design
for read-only single-workspace tokens is in `agents/mcp/README.md`.

### Discover results in the browser (W9-2, no new endpoints)

Filters on loaded results (media type, running / has a stop date, CTA, landing
domain, minimum run length) work in memory on what is already loaded and never
call the API. Infinite scroll and "Load more" read the next page of
`GET /api/discovery/jobs/{job_id}/results`, which reads stored rows only
(0 Metapi records). Keyboard: `j`/`k` move, `s` saves (`POST
/api/creatives/{id}/save`), `o` opens the permalink, `?` shows the list.

## 6. Account, team, support, notifications

- `/api/account`: `profile` (GET/PATCH), `avatar`, `access`, `access-requests`,
  `access-grants`, `usage/today`, `workspace`, `onboarding-complete`, and team
  invites/members (`team_accounts`, flag-hidden in the UI).
- `GET /api/account/record-usage` (W9-1): the active workspace's Metapi
  records this UTC month: `{period_start, used, cap, remaining, percent,
  warning, reached, estimates: {discover_search, monitor_run,
  monitor_month: {daily, weekly}}}`. `warning` is true at 80% of `cap`.

### Record budget guardrails (W9-1)

Metapi bills each returned ad as a record. Every Metapi task reserves its
`count` against both the global `METAPI_MONTHLY_RECORD_BUDGET` (unchanged) and
the workspace's monthly cap in one transaction; a refusal by either rolls back
both. The cap is `plans.limits.records_per_month` (set by an admin in the plan
editor, `PUT /api/admin/plans/{id}`, 0–100000) or
`METAPI_WORKSPACE_MONTHLY_RECORD_CAP` (default 300). Usage is
`workspace_daily_usage.metapi_records`, summed over the month; refunds never
lower it. A search or monitor run reserves at most `METAPI_RESOLVE_COUNT` + 15
records (30 by default). `POST /api/discovery/jobs` (after cache hits, which
are free) and creating or re-activating a monitor return `429` with
`{code: "workspace_record_cap_reached", message, used, cap, needed}` when the
month has less room than that. Scheduled monitor runs are refused by the
reservation itself.
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
