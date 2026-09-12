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
pip install -r requirements.txt
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
- **First request after idle**: Takes ~10–30s (occasionally up to ~45s) while Render boots the container and Neon re-attaches Postgres.
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
| `USE_MOCKS` | ✅ | **Must be `false` in production.** When `true`, sign-in always returns a fake admin token regardless of credentials. |
| `PUBLIC_API_BASE_URL` | ✅ (prod) | Public API base for webhooks, e.g. `https://helix-intelligence-ai.onrender.com/api` |
| `HF_API_KEY_ID` | ✅ (for Create) | Higgsfield API Key ID |
| `HF_API_KEY_SECRET` | ✅ (for Create) | Higgsfield API Key Secret |
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
| `AIHUBMIX_API_KEY` | Optional | AIHubMix tertiary LLM inference |
| `TOKENHARBOR_API_KEY` | Optional | Token Harbor quaternary LLM inference |
| `GEMINI_API_KEY` | Optional | Google Gemini final LLM inference fallback |

### Frontend (Vercel)

The frontend builds on Vercel. **Two env vars must be set at build time** (Vercel → Settings → Environment Variables):

```
VITE_DATA_SOURCE=api
VITE_API_BASE_URL=https://helix-intelligence-ai.onrender.com/api
```

The URL **must be absolute** — a relative `/api` path will 404 because the frontend and backend live on different origins.

### ⚠️ Production frontend ↔ backend connectivity

The Vite dev proxy in `vite.config.js` (`/api → http://127.0.0.1:8000`) **only works during local development**. It has no effect in a production build.

Without the two env vars above, sign-up/sign-in and all other API calls will fail with network errors in production while working fine locally. This is the single most common "it works on my machine" deployment issue.

## Media storage

Generated media is written to **Cloudflare R2** over the S3-compatible API
(`backend/app/services/storage_service.py`).

Render's filesystem is ephemeral: anything written locally is destroyed on the
next restart or deploy, while the database keeps pointing at a URL that now
404s. R2 is what makes generated media survive.

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

The sweep runs at startup **and** on a 60s timer. Startup alone is not enough:
a restart that comes back in seconds kills a job that is not yet old enough to
look stale, and nothing would ever revisit it.

The UI distinguishes the two failure causes. `failure_kind` is surfaced on both
the discover `Job` and the media job response, and Discover and Create render
"interrupted by a service restart" separately from a genuine error, so a user
is never told to fix a query or prompt that was fine.

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
`feature_name="monitors"`. Feature flags default to allowed, so admins can
disable monitors per organisation via `custom_feature_flags` without a schema
change. There is no separate paid tier.

Blocked runs do not retry forever. A trial expiry, disabled feature or exhausted
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
against the mock (`authService` is the API client in every data-source mode,
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

### Credit Cost Table
| Action | Credits | Description |
|---|---|---|
| `discover_job` | 2.0 | Base ad library search & creative scraping |
| `discover_deep_fallback` | +3.0 | Bright Data deep search surcharge (only if prior sources return 0) |
| `create_image` | 3.0 | Higgsfield or AI image generation |
| `create_video` | 8.0 | Higgsfield video/motion generation |
| `ai_insight` | 1.0 | Single creative deep LLM insight |
| `pattern_pack` | 1.0 | Pattern synthesis across scraped ads |
| `ai_chat` | 0.5 | Interactive creative AI chat query |

### Trial Defaults
- **Plan ID**: `plan_trial_default` (7-Day Free Trial)
- **Initial Credit Balance**: `25.0` credits
- **Daily Credit Limit**: `3.5` credits/day (resets daily at `00:00:00 UTC`)
- **Trial Duration**: 7 days from user registration (`trial_expires_at`)
- **Admin Role**: Bypasses all quota and credit limits (`role="admin"`).

### Standardized Error Responses
- `402 Payment Required` (Insufficient credits):
  ```json
  {
    "detail": {
      "code": "insufficient_credits",
      "message": "Not enough credits for this action (1.0 available, 3.0 required). Upgrade or wait for trial reset.",
      "credit_balance": 1.0,
      "required": 3.0,
      "plan_name": "7-Day Free Trial"
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
- `403 Forbidden` (`trial_expired` or `feature_disabled`).

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
- **Honest Zero-Results**: Never fakes mock creatives in production (`USE_MOCKS=false`). Returns clear report of all attempted sources.

---

## Higgsfield Create Integration

### Official Authentication Format
Higgsfield requires API Key credentials formatted with `Key` (never `Bearer`):

- **Header**: `Authorization: Key {HF_API_KEY_ID}:{HF_API_KEY_SECRET}`
- **Base URL**: `https://api.higgsfield.ai`
- **Default Image Endpoint**: `https://api.higgsfield.ai/higgsfield-ai/soul/v2/standard`
- **Webhook Param**: `?hf_webhook={URL_ENCODED_PUBLIC_API_URL}/webhooks/higgsfield`

### Operator Proof Curl
```bash
export HF_API_KEY_ID="your_key_id"
export HF_API_KEY_SECRET="your_key_secret"
curl -s -w "\nHTTP %{http_code}\n" -X POST \
  "https://api.higgsfield.ai/higgsfield-ai/soul/v2/standard" \
  -H "Authorization: Key ${HF_API_KEY_ID}:${HF_API_KEY_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A quiet alpine lake at sunrise, editorial photography"}'
```

---

## 7-Day Trial & Gemini Image Generation

HELIX provides a 7-day free trial with daily image creation powered by the existing `GEMINI_API_KEY`:

### Entitlement Rules:
- **Trial Duration**: 7 days from signup (`trial_started_at` to `trial_expires_at`).
- **Trial Daily Quota**: 5 image generations per UTC day (resets at 00:00 UTC).
- **Trial Total Cap**: 25 total image generations across the entire trial.
- **Video Generation**: Disabled during trial; available exclusively on paid plans.
- **Paid Plans**: 50+ images per day.
- **Admin Users**: Unlimited bypass across all features.

### Environment Configuration:
- `GEMINI_API_KEY`: *(Required server-side only)* Google Gemini API key. Never exposed to browser or client.
- `GEMINI_IMAGE_MODEL`: `gemini-3.1-flash-image` (default stable image model).
- `TRIAL_DAYS`: `7`
- `TRIAL_IMAGES_PER_DAY`: `5`
- `TRIAL_IMAGES_TOTAL`: `25`
- `PAID_IMAGES_PER_DAY`: `50`

### Running the Gemini Image Live Smoke Test:
To execute a real development smoke test against Google Gemini's image API:
```bash
ENABLE_GEMINI_LIVE_TEST=true python backend/scripts/test_gemini_image_live.py
```

### Running the Test Suites:
```bash
# Run Gemini Trial & Entitlement suite
python backend/tests/test_gemini_trial_suite.py

# Run Higgsfield Diagnostic suite
python backend/tests/test_higgsfield_suite.py
```



