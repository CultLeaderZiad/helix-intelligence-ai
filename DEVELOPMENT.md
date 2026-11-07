# Development

## Running locally

### Frontend (Vite)
```bash
pnpm install
pnpm dev
```
The frontend runs at `http://localhost:3000`.

### Backend (FastAPI)
```bash
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Mac/Linux
pip install -r requirements.txt        # add -dev.txt to run tests: pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```
The backend API runs at `http://localhost:8000/api`.

## Environment Variables

All secrets (like `DATABASE_URL`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `SCRAPEGRAPH_API_KEY`, `SECRET_KEY`) are read securely from the environment. They should be set in a `.env.local` file for local development and in the deployment dashboard for production.

## Deployment

### Backend (Render)

The backend runs on Render (free tier). Configuration is in `render.yaml`.

**Cold starts expected; first request after idle 10–30s:**
The Render free web tier spins down instances after 15 minutes of inactivity, and Neon Postgres free compute also suspends when idle. As a result:
- **First request after idle**: Takes ~10–90s (74s measured on 2026-11-06) while Render boots the container and Neon re-attaches Postgres.
- **Frontend handling**: The UI automatically handles cold-start latency:
  - `ProtectedRoute` shows a clean `"Starting Helix services…"` waking hold instead of a blank screen.
  - Auth bootstrap automatically retries once on network/gateway timeouts.
  - Auth forms & data tables display `"Starting Helix services…"` with a 1-click **Retry** button rather than cryptic auth failures.

#### Health Check & Keep-Warm Options (Optional)
To check backend health and warm up the container:
- **Health URL (Fast)**: `GET https://helix-intelligence-ai.onrender.com/health` (or `/`)
- **API Diagnostics**: `GET https://helix-intelligence-ai.onrender.com/api/health`

**External Keep-Warm Options (User Choice):**
You can set up a free uptime monitor or cron ping to reduce cold starts:
1. **UptimeRobot / Cron-Job.org / BetterStack (Free)**:
   - Target URL: `https://helix-intelligence-ai.onrender.com/health`
   - Frequency: Every **5–10 minutes**
   - HTTP Method: `GET`
2. **Note on Free Tier Limits**:
   - Render free tier includes 750 free instance hours/month (enough for one service running continuously).
   - Even with pings, Render may occasionally cycle or sleep instances; pinging significantly reduces idle spin-downs but does not promise enterprise 100% warm SLA.


#### Backend env vars (set in Render Dashboard → Environment)

| Variable | Required | Notes |
|----------|----------|-------|
| `SECRET_KEY` | ✅ | JWT signing key. Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `DATABASE_URL` | ✅ | Neon Postgres connection string (with asyncpg driver) |
| `BACKEND_CORS_ORIGINS` | ✅ | Comma-separated origins, **must include the Vercel URL exactly** (scheme + host, no trailing slash): `https://helix-intelligence-ai-six.vercel.app,http://localhost:5173,http://localhost:3000` |
| `BACKEND_CORS_ORIGIN_REGEX` | Optional | Lets Vercel **preview** URLs call the API. Must start with `^https://`, end with an escaped domain and `$`, and must not use `.*`/`.+`. For this project: `^https://helix-intelligenc[a-z0-9-]*-flutterdevelopers25-6172s-projects\.vercel\.app$` |
| `PUBLIC_API_BASE_URL` | ✅ (prod) | Public API base for webhooks, e.g. `https://helix-intelligence-ai.onrender.com/api` |
| `R2_ACCOUNT_ID` | ✅ (prod) | Cloudflare R2 account id — see "Media storage" below |
| `R2_ACCESS_KEY_ID` | ✅ (prod) | R2 API token access key id |
| `R2_SECRET_ACCESS_KEY` | ✅ (prod) | R2 API token secret |
| `R2_BUCKET` | ✅ (prod) | R2 bucket name, e.g. `helix-media` |
| `R2_PUBLIC_BASE_URL` | ✅ (prod) | Bucket public read origin, e.g. `https://pub-xxxx.r2.dev` |
| `CRON_SECRET` | ✅ (for Monitors) | Shared secret for `POST /api/monitors/tick`. Unset ⇒ the endpoint returns 503 and no monitor runs. See "Monitors" below |
| `APP_BASE_URL` | ✅ (for Monitors) | Frontend origin used for links in alerts. Production: `https://helix-intelligence-ai-six.vercel.app` |
| `MONITOR_MAX_PER_TICK` | Optional | Due monitors started per tick (default `3`) |
| `MONITOR_MISS_THRESHOLD` | Optional | Consecutive absences before an ad is reported stopped (default `2`) |
| `MONITOR_MAX_FAILURES` | Optional | Consecutive failed runs before a monitor self-pauses (default `5`) |
| `RESEND_API_KEY` | Optional | Resend API key. Without it monitor alerts are in-app only |
| `RESEND_FROM` | Optional | Verified sender address, e.g. `alerts@yourdomain.com` |
| `META_ACCESS_TOKEN` | Optional | Meta Marketing / Ad Library API access |
| `APIFY_API_TOKEN` | Optional | Apify Actor scraper API token |
| `BRIGHTDATA_API_KEY` | Optional | Bright Data scraping proxy API key |
| `ADYNTEL_API_KEY` | Optional | Adyntel ad intelligence API key |
| `ADYNTEL_EMAIL` | Optional | Adyntel account email |
| `SCRAPEGRAPH_API_KEY` | Optional | ScrapeGraph AI landing page enrichment |
| `GROQ_API_KEY` | Optional | Groq primary LLM inference (Llama 3.3 70B) |
| `OPENROUTER_API_KEY` | Optional | OpenRouter secondary LLM inference |
| `GEMINI_API_KEY` | Optional | Google Gemini final LLM inference fallback |

### Frontend (Vercel)

The frontend (Vercel) and the API (Render) are on **different origins**, and
`vercel.json` sends every unknown path to `index.html`. A relative `/api` in a
deployed build therefore returns the SPA's HTML instead of FastAPI, and
sign-up shows "Unable to create account". Deployed builds must call the
absolute Render URL.

`.env.production` (committed, not a secret) already sets:

```
VITE_DATA_SOURCE=api
VITE_API_BASE_URL=https://helix-intelligence-ai.onrender.com/api
```

so production **and** preview builds reach the real API even with no Vercel
variable. Vercel → Settings → Environment Variables overrides it per scope:

| Variable | Production | Preview | Notes |
|---|---|---|---|
| `VITE_API_BASE_URL` | `https://helix-intelligence-ai.onrender.com/api` | same, or a staging API's HTTPS URL | Build-time. Must be `https://` on a DNS host; no trailing slash. Redeploy after changing it |
| `VITE_ENVIRONMENT` | `production` (or unset) | `preview` (or unset) | Optional. `preview`/`staging` builds may use a public HTTPS API; `development`/`test` stay loopback-only (`src/services/origin.js`) |
| `VITE_NEON_AUTH_URL` | unset | unset | Not used. Auth is FastAPI JWT |

Note: a preview build talks to whatever API it points at. Pointing previews at
the production Render API means preview sign-ups create production accounts
and preview-only backend routes (newer than what Render runs) return 404.

#### CORS on Render (must match the Vercel origins)

Set on the Render web service → Environment (no secret values here):

```
BACKEND_CORS_ORIGINS=https://helix-intelligence-ai-six.vercel.app,http://localhost:5173,http://localhost:3000
BACKEND_CORS_ORIGIN_REGEX=^https://helix-intelligenc[a-z0-9-]*-flutterdevelopers25-6172s-projects\.vercel\.app$
```

Vercel preview hosts look like
`helix-intelligenc-git-<branch-hash>-flutterdevelopers25-6172s-projects.vercel.app`.
`BACKEND_CORS_ORIGIN_REGEX` only takes effect once the backend running on
Render includes it (W8; Render deploys `main` only). Until then, add the branch's exact preview origin to
`BACKEND_CORS_ORIGINS`. A rejected preflight returns **400** with no
`access-control-allow-origin` header; the browser then reports a network error.

#### Region and cold starts (verified 2026-11-06)

Already colocated, so nothing to move: the Render web service
`helix-intelligence-ai` runs in **Ohio** and the Neon project
`helix-intelligence` is in **aws-us-east-2 (Ohio)**. Keep any new service or
database there.

The service is on Render's **free** plan, so it sleeps when idle. The first
request after sleep took **~74 s** (`GET /health`); once awake,
`GET /api/health` answers in ~0.3 s with `{"db":"connected"}`. A sign-up
submitted during that wake-up can look broken. Optional ways to fix it, each
a dashboard decision for the owner:

- Keep-warm ping (free): an uptime monitor hitting `/health` every 5–10 min
  (see "Health Check & Keep-Warm Options" above).
- Set the service's **Health Check Path** to `/health` (currently empty).
- Move to a paid instance type that does not sleep. Not done: the owner
  prefers free/cheap plans until there are paying customers.

Render deploys **`main` only** (auto-deploy on commit, PR previews off). Code
on a feature branch, including `BACKEND_CORS_ORIGIN_REGEX` support, is not
live on Render until it is merged to `main`.

#### Verify sign-up against a deployment

1. Preflight (read-only):
   `curl -si -X OPTIONS https://helix-intelligence-ai.onrender.com/api/auth/sign-up -H "Origin: <vercel origin>" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: content-type"`
   → expect `200` and `access-control-allow-origin: <vercel origin>`.
2. Bundle check: open the deployment, DevTools → Network, submit sign-up.
   The request must go to `https://helix-intelligence-ai.onrender.com/api/auth/sign-up`,
   not `<vercel host>/api/...`.
3. Sign up with a real inbox you own, then sign in. Expect `201`/`200` and a redirect into the app.
4. If it shows "Starting Helix services…", Render is cold-starting; retry after ~30 s.

#### Local frontend against the live API (http://localhost:3000)

```bash
pnpm dev:live
```

Runs the normal dev server on http://localhost:3000 in mode `live`.
`.env.live` sets `HELIX_DEV_API_TARGET=https://helix-intelligence-ai.onrender.com`,
so the Vite proxy forwards `/api` and `/uploads` to Render instead of a local
FastAPI on :8000. The browser still calls same-origin `/api`, so `origin.js`
and CORS are unchanged. `HELIX_DEV_API_TARGET` is not `VITE_`-prefixed and
never reaches the bundle. Anything you do here (sign-ups, searches) is real
production data. `pnpm dev` keeps using the local backend.

### ⚠️ Production frontend ↔ backend connectivity

The Vite dev proxy in `vite.config.js` (`/api → http://127.0.0.1:8000`) **only works during local development**. It has no effect in a production build.

## Media storage

Uploaded files (avatars) are written to **Cloudflare R2** over the S3-compatible API
(`backend/app/services/storage_service.py`).

Render's filesystem is ephemeral: anything written locally is destroyed on the
next restart or deploy, while the database keeps pointing at a URL that now
404s. R2 is what makes stored files survive.

**All five `R2_*` variables must be set together.** A partial configuration
disables R2, logs an error, and falls back to local disk. `R2_PUBLIC_BASE_URL`
is mandatory on purpose — without a public origin the only alternative is a
presigned URL, which expires within seven days and would silently rot in the
database.

Setup, once:

1. Cloudflare dashboard → R2 → enable. **This requires a card or PayPal on the
   account even though the free tier (10 GB, zero egress) is never billed** —
   it is anti-abuse verification.
2. Create a bucket, e.g. `helix-media`.
3. Bucket → Settings → enable public access, and copy the `pub-….r2.dev`
   origin into `R2_PUBLIC_BASE_URL` (or attach a custom domain).
4. R2 → Manage API Tokens → create an **Object Read & Write** token scoped to
   that bucket; copy the access key id and secret.

### Local media fallback

When R2 is unset, media goes to `backend/uploads/` and is served by
`app/api/routers/uploads.py`. That route replaced a `StaticFiles` mount that
served every file to anyone who could guess a name. Access now requires either
a signature (a capability URL, the same model as a presigned S3 link, which is
what lets an `<img>` tag work without an `Authorization` header) or an
authenticated caller who owns the media job. Everything else gets a 404 so the
endpoint cannot be used to enumerate filenames.

## Job restart resilience

Background work runs as `asyncio` tasks inside the web process, so a restart or
deploy kills any job in flight while its database row stays `running` forever.

`backend/app/services/job_reconciliation.py` marks those jobs failed with
`failure_kind='service_restart'`, and refunds discover jobs — those charge
upfront, so an interrupted run took money for a result the user can never
receive. Media only charges on success, so there is nothing to refund there.

A job is treated as dead when it is owned by a **different process lifetime**
(`owner_boot_id`) **and** has been silent past `JOB_STALE_AFTER_S` (120s).
Silence, not total age, is the signal: a live job writes `heartbeat_at` every
`JOB_HEARTBEAT_INTERVAL_S` (15s). This matters because real discovery runs in
this app reach 5.3 minutes at p95, so an age-based rule would have to wait out
the slowest legitimate job — roughly ten minutes — before it could call
anything dead.

The jobs worker (`backend/workers/jobs`) runs the sweep at startup **and** on a 60s timer,
using `worker_session_maker` for maintenance and refunds. The API does not run
startup sweeps or periodic maintenance; keep the worker service running for
recovery. Startup alone is not enough: a restart that comes back in seconds
kills a job that is not yet old enough to look stale, and nothing would revisit
it. Failed scrape refund recovery considers only the last 24 hours using
`COALESCE(completed_at, heartbeat_at, created_at)` (scrape jobs have no
`updated_at` column); sweeping an active scrape sets `completed_at` to now.
Monitor cleanup resolves the parent organization while the stale run is still
`running`, then marks it failed and retains that org for tenant-scoped notices.

The UI distinguishes the two failure causes. `failure_kind` is surfaced on the
discover `Job`, and Discover renders "interrupted by a service restart"
separately from a genuine error, so a user is never told to fix a query that
was fine.

### Known limit of the current approach

Jobs run in-process via `asyncio.create_task`, which is a deliberate choice
while hosting cost still matters more than throughput. The practical ceiling is
concurrency: every in-flight scrape holds a task, provider HTTP connections and
a heartbeat writer inside the single Render web instance, competing with
request handling on the same event loop. Discovery is IO-bound so this is fine
at low tens of concurrent jobs, but there is no queue, no backpressure and no
admission control — a burst is accepted rather than queued, and a restart
cancels all of them at once. A real worker queue is the fix when volume
justifies the hosting cost.

## Monitors (scheduled competitor watches)

A monitor is a saved Discover query that re-runs on a cadence and reports what
changed. It reuses the existing pipeline rather than introducing a queue: the
scheduler calls one endpoint, and due monitors are started as `asyncio` tasks on
the same web instance, exactly like an interactive search.

### Scheduling

`POST /api/monitors/tick` with the shared secret in an `X-Cron-Secret` header
claims every due monitor and starts it. It returns as soon as the runs are
dispatched, because a discovery run takes minutes — far longer than any cron
provider will hold a request open.

Render Cron Jobs are a **paid** service type ($1/month minimum), so the tick was
deliberately built as an ordinary authenticated endpoint instead of a
Render-only feature. Any scheduler works, including the free ones already used
to keep the instance warm. Every 15 minutes is a sensible schedule; cadence is
enforced per monitor, so ticking more often than a monitor's cadence does
nothing.

```bash
curl -fsS -X POST -H "X-Cron-Secret: $CRON_SECRET" \
  https://helix-intelligence-ai.onrender.com/api/monitors/tick
```

While `CRON_SECRET` is unset the endpoint returns 503 to everyone. An
unconfigured deployment is closed rather than exposing a way to spend an
organisation's credits.

Claiming is atomic: the statement that selects due monitors also pushes
`next_run_at` forward and takes `FOR UPDATE SKIP LOCKED`, so two overlapping
ticks cannot both pick up the same monitor and charge for it twice.
`MONITOR_MAX_PER_TICK` caps how many start at once.

### Billing

A monitor run costs exactly what a Discover search costs and goes through the
same gatekeeper (`assert_can_spend`) against the **monitor owner's** plan, with
`feature_name="monitors"`. Feature flags fail closed. A platform admin grant
is what turns a feature on. There is no separate paid tier.

Blocked runs do not retry forever. A disabled feature or exhausted
balance pauses the monitor and notifies the owner once; a daily cap only defers
it to the next cadence, since that clears on its own.

A failed monitor run is billed the same way as a failed Discover search: the
credit stays charged. The owner is told via an in-app notification, and via
email once Resend is configured, so an unattended failure is visible without a
separate refund rule.

### Change detection

This is the only genuinely new logic, and it is a heuristic — see
`creative_fingerprint.py`, where every rule is written out. None of the ad
library providers return a stable advertiser ad ID (`RawCreative` has no such
field, and `brand_id` is a fresh UUID per job), so identity is reconstructed
from the ad's own content. Each creative gets two hashes:

- **identity** — platform, landing domain, format and the normalized headline.
  What makes this "the same ad" across runs.
- **content** — normalized headline, body and CTA. What it currently says.

Splitting them is what makes `copy_changed` possible at all; if body and CTA
were part of identity, an edited ad would look like one ad dying and another
being born. Normalization strips case, accents, punctuation and unresolved
merge tags like `{{product.brand}}`, none of which mean the ad changed.

Three refusals to report keep the feed trustworthy:

- **The first run emits nothing.** It records a baseline. Telling a user they
  have forty new ads on day one is noise, not intelligence.
- **An empty scrape emits nothing.** A zero-result run is indistinguishable
  from a provider outage, and "all your competitor's ads were killed" is the
  most damaging thing this feature could get wrong. The run is recorded as
  inconclusive.
- **A single absence is not a death.** An ad must be missing for
  `MONITOR_MISS_THRESHOLD` consecutive runs before `killed_ad` fires, because
  one absence is far more often a partial scrape than a paused ad.

Known limit: ads that normalize identically (same copy, same domain — or no
copy at all) are disambiguated by a deterministic index, so the first copy stays
comparable across runs but surplus duplicates churn if their count changes.
That is inherent to having no provider ad ID.

### Delivery

In-app notifications via the existing notification service, plus optional email
through Resend. Email is credential-driven like R2: without both
`RESEND_API_KEY` and `RESEND_FROM` the send is skipped with a log line and the
run still succeeds. Until a domain is verified, `RESEND_FROM` can be
`Helix Intelligence <onboarding@resend.dev>` and will only deliver to the
Resend account's own inbox (plus Resend's `delivered@resend.dev` test sink).
Slack and outbound webhooks are deliberately not built yet.

## Auth Architecture

Sign-in / sign-up go **directly to the FastAPI backend** (Render) via JWT HS256.
There is **no** Neon Auth / Better Auth dependency on the login path.

- Frontend: `VITE_API_BASE_URL` → POST `/api/auth/sign-in` or `/api/auth/sign-up`
- Backend returns `SessionResponse` with `access_token` (HS256 JWT)
- Token stored in `localStorage` as `helix_access_token`
- All subsequent requests send `Authorization: Bearer <token>`
- `GET /api/auth/session` validates the JWT and returns the current user

Do **not** set `VITE_NEON_AUTH_URL` — it is no longer used and was the cause of the "Invalid origin" error in production.

Auth is always backed by the FastAPI service — the frontend never signs in
against a mock (`authService` is always the API client,
so a real account always works).

### Password reset ("auth failed" recovery)

Accounts created before the FastAPI cutover (or via the Neon webhook) carry a
password hash the app cannot verify, so sign-in returns the generic
`Invalid email or password`. Recovery is:

1. `POST /api/auth/forgot-password` — always returns the same generic success
   (no account enumeration). For an existing account it mints a single-use,
   30-minute JWT with `purpose: password_reset` (stored only as SHA-256).
2. The link is logged server-side on every request. Because no mail provider
   is configured yet, `AUTH_DEV_RESET_RETURN=true` additionally returns it in
   the API response (`{"ok": true, "reset_url": "…"}`), which the
   forgot-password page renders. Set it to `false` as soon as real email
   delivery is wired up.
3. `POST /api/auth/reset-password` redeems the token (single-use — a reused or
   expired token is rejected) and returns a fresh session, signing the user in.

Locked out as the owner? Run the recovery tool against the same database the
API uses (no deploy needed):

```bash
cd backend
python scripts/reset_admin_password.py --email you@gmail.com --password 'NewPassword2026!'
```

### Credit & Billing Architecture

Helix enforces strict server-side credit caps with database row-level locking (`with_for_update()`) on organizations to prevent race conditions and protect external provider quotas.

### Credit costs

Charged server-side by `assert_can_spend`; the values live in
`backend/app/services/billing_service.py` and are the source of truth.

| Action | Credits |
|---|---|
| Discover search | 1.0 |
| Discover deep search surcharge | 2.0 |

Access is granted by a platform administrator; there is no trial, plan
purchase or checkout. A new workspace starts on the default plan with every
feature off until an admin grants access.

### Standardized Error Responses
- `402 Payment Required` (Insufficient credits):
  ```json
  {
    "detail": {
      "code": "insufficient_credits",
      "message": "Not enough credits for this action (1.0 available, 3.0 required). Ask a workspace administrator for more credits.",
      "credit_balance": 1.0,
      "required": 3.0,
      "plan_name": "Granted"
    }
  }
  ```
- `429 Too Many Requests` (Daily limit reached):
  ```json
  {
    "detail": {
      "code": "daily_limit_reached",
      "message": "Daily credit limit reached (3.5 credits/day). Used 3.5 of 3.5 credits today. Resets at 00:00 UTC.",
      "daily_limit": 3.5,
      "daily_used": 3.5,
      "daily_remaining": 0.0,
      "resets_at_utc": "2026-08-31T00:00:00+00:00"
    }
  }
  ```
- `403 Forbidden` (`feature_disabled`, or access not granted).

---

## Competitor Ad Library Provider Chain

Discover uses an ordered, cost-aware canonical chain to avoid unnecessary API costs:

```text
1. Adyntel (fast company/domain ad search if ADYNTEL configured)
2. Apify (Facebook Ad Library actor if APIFY configured)
3. Meta Graph API (optional official boost if META_ACCESS_TOKEN configured)
4. Bright Data (Controlled deep fallback ONLY IF:
   - prior providers returned 0 usable creatives, AND
   - plan allows deep_search, AND
   - organization has >= 3.0 credits for deep surcharge)
5. ScrapeGraph Enrichment (capped at top 2 landing pages)
```

- **Query Caching**: Succeeded queries are cached for **12 hours** per organization. Duplicate searches within 12 hours return cached jobs instantly with 0 credits deducted.
- **Honest Zero-Results**: Never fakes creatives; there is no mock mode. Returns clear report of all attempted sources.

---

## Row-level security roles

Row-level security stays enabled on tenant tables. Restricted API/worker roles
are denied by default when no organization context is set; the only broad
application bypass is the existing `helix.platform_admin` setting. The forward
RLS correction removes `FORCE ROW LEVEL SECURITY` so a table owner/migration
role retains normal owner access. Superusers and roles with `BYPASSRLS` (the
Neon owner, often `neondb_owner`) also bypass policies. Production refuses to
boot when `current_user` is one of those roles; other environments log a
warning and continue.

`helix_app` and `helix_worker` are `NOLOGIN` group roles. Migration
`e7c1a9b4d2f0` creates them transactionally with its schema changes; a failure
rolls back both. Create one login for the API and one for the worker. Set the
password in the Neon or Render dashboard, not in this repository.

```sql
CREATE ROLE helix_api_login LOGIN NOSUPERUSER NOBYPASSRLS INHERIT;
CREATE ROLE helix_worker_login LOGIN NOSUPERUSER NOBYPASSRLS INHERIT;
GRANT helix_app TO helix_api_login;
GRANT helix_worker TO helix_worker_login;
```

The policy denies access without matching organization context, independent
of `helix.enforce`; no login-role setting is needed. Maintenance policies are
worker-only, so API logins must not inherit `helix_worker`.

Then set each password out of band (`ALTER ROLE ... PASSWORD` from a secret
store) and point `DATABASE_URL` at that login. The API uses
`helix_api_login`. The jobs worker uses `helix_worker_login`. Both
inherit `SELECT, INSERT, UPDATE, DELETE` on public tables and `USAGE, SELECT`
on sequences. Migration `d4f6a8c0e2b1` grants those privileges again and sets
default privileges for tables created later by the migration role.


## First platform admin

A new database has no platform admin, so nobody can open the admin pages to
grant access. `backend/scripts/bootstrap_platform_admin.py` promotes one named
account and grants its own workspace access, using the same services as the
admin API (`update_user_role`, `grant_organization_access`). Every change is
written to the audit log (`admin_user_role_updated`, `access_granted`,
`platform_admin_bootstrap`).

- It selects the account by `users.id` only, never by email.
- It refuses to run unless `--expect-branch` equals the Neon branch id the
  server reports. Use `local` for a non-Neon Postgres.
- Without `--apply` it is a dry run.
- Re-running it changes nothing. Features granted earlier are kept.
- It never prints passwords, emails or connection strings.
- It runs as the API login (`helix_api_login`) or the owner. It sets the
  platform-admin RLS scope itself.

Rehearsed on the production copy `w8-rehearsal` on 2026-11-07, as a restricted
`helix_app` login, with a disposable account. The account was promoted, its
workspace got Discover, and a second run changed nothing. An ordinary account
still gets `403` on `/admin/*`, `access-grant` and `/account/access-grants`.

### Production procedure (needs Ziad's approval; not run yet)

1. **Rollback point.** Create a Neon branch from `production`, for example
   `pre-admin-bootstrap`.
2. **Account.** Ziad signs up on the live app with his own email. In the Neon
   SQL editor (production), he looks up his id and confirms it is his account:
   ```sql
   SELECT id, created_at FROM users WHERE lower(email) = lower('<his email>');
   ```
3. **Login roles.** As the owner, check both role memberships. Grant only the
   ones that are missing:
   ```sql
   SELECT pg_has_role('helix_api_login', 'helix_app', 'MEMBER'),
          pg_has_role('helix_worker_login', 'helix_worker', 'MEMBER');
   GRANT helix_app TO helix_api_login;          -- only if false
   GRANT helix_worker TO helix_worker_login;    -- only if false
   ```
4. **Dry run.** Render's free plan has no shell, so Ziad runs this from his own
   machine, in a fresh terminal, with two variables set for that terminal only:
   - `DATABASE_URL`: the `helix_api_login` connection string from the Neon
     console.
   - `ALLOWED_REMOTE_DATABASE_HOST`: that string's host.

   Don't save either variable to a file. The production branch id is
   `br-soft-mode-ax44ab32`. Check the printed `user_id`, `org_id` and flags.
   ```bash
   cd backend
   python scripts/bootstrap_platform_admin.py --user-id <id> --expect-branch br-soft-mode-ax44ab32
   ```
5. **Apply.** Run the same command again with `--apply`. Add
   `--features discover,swipe_files,monitors` if those should be on too. Note
   the printed `grant_id`.
6. **Verify.** Sign in. `/admin` should load and Access & Usage should show
   approved. `GET /api/auth/session` should return `is_platform_admin: true`
   and `feature_flags.discover: true`.

The promotion is committed before the grant. If the grant step fails, re-run
the same command: it skips the promotion and retries only the grant.

### Rollback

- **Access only:** in Admin → Access requests, revoke the workspace, or call
  `POST /api/admin/organizations/<org_id>/access-revoke`. The grant row stays,
  marked revoked.
- **Admin rights:** as the owner, run
  `UPDATE users SET role = 'customer', is_platform_admin = false WHERE id = '<id>';`.
  This leaves the app with no admin until the procedure is run again.
- **Login roles:** do not revoke them unless the whole release is rolled back.
  Without them the API and worker cannot read any table.
- **Everything:** restore from `pre-admin-bootstrap`, or use Neon's
  point-in-time restore to just before step 3. This also discards anything
  written after that point.
