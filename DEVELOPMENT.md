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
| `PUBLIC_API_BASE_URL` | ✅ (prod) | Public API base, e.g. `https://helix-intelligence-ai.onrender.com/api` |
| `METAPI_API_KEY` | For Discover | Metapi live Meta Ad Library search — the only ad-search provider |
| `META_ACCESS_TOKEN` | Optional | Meta official Graph API `ads_archive` token. Coverage is limited to political/social-issue ads worldwide or any ad delivered to EU/UK — it does not answer generic commercial keyword searches. |
| `BRIGHTDATA_API_KEY` | Optional | Bright Data scraping proxy API key (no scraper currently implemented against it) |
| `SCRAPEGRAPH_API_KEY` | Optional | ScrapeGraph AI landing page enrichment |
| `GROQ_API_KEY` | Optional | Groq primary LLM inference (Llama 3.3 70B) |
| `OPENROUTER_API_KEY` | Optional | OpenRouter secondary LLM inference |
| `AIHUBMIX_API_KEY` | Optional | AIHubMix tertiary LLM inference |
| `TOKENHARBOR_API_KEY` | Optional | Token Harbor quaternary LLM inference |
| `GEMINI_API_KEY` | Optional | Google Gemini final LLM inference fallback; also powers Create image generation |

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
| `discover_job` | 2.0 | Base ad library search & creative scraping (Metapi) |
| `create_image` | 3.0 | Gemini image generation |
| `create_video` | 8.0 | Pollinations video/motion generation |
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

Discover searches exclusively via Metapi, the only configured ad-search provider:

```text
1. Metapi (live Meta Ad Library search via METAPI_API_KEY)
```

Adyntel, Apify, and the official Meta Graph API were removed from the chain:
Adyntel/Apify added no coverage beyond Metapi, and the free Meta Graph
`ads_archive` endpoint only archives political/social-issue ads worldwide or
ads delivered to EU/UK audiences — it cannot answer a generic commercial
keyword search, so it never usefully fired as a fallback.

- **Query Caching**: Succeeded queries are cached for **12 hours** per organization. Duplicate searches within 12 hours return cached jobs instantly with 0 credits deducted.
- **Honest Zero-Results**: Never fakes mock creatives in production (`USE_MOCKS=false`). Returns a clear zero-results report when Metapi is unconfigured or finds nothing.

---

## Create Media Generation

All Create requests route through Google Gemini (images) or Pollinations
(video). Higgsfield has been removed as a provider.



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
```



