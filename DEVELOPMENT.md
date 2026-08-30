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

## Auth Architecture

Sign-in / sign-up go **directly to the FastAPI backend** (Render) via JWT HS256.
There is **no** Neon Auth / Better Auth dependency on the login path.

- Frontend: `VITE_API_BASE_URL` → POST `/api/auth/sign-in` or `/api/auth/sign-up`
- Backend returns `SessionResponse` with `access_token` (HS256 JWT)
- Token stored in `localStorage` as `helix_access_token`
- All subsequent requests send `Authorization: Bearer <token>`
- `GET /api/auth/session` validates the JWT and returns the current user

Do **not** set `VITE_NEON_AUTH_URL` — it is no longer used and was the cause of the "Invalid origin" error in production.

## Credit & Billing Architecture

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

## Database (Neon)

The FastAPI backend is backed by Neon Postgres. The `plan_trial_default` plan row must exist for full session responses. If missing, the backend returns a graceful minimal session.

The frontend has **no** direct database dependency.

## Adding a page (Lazy Loading Convention)

To ensure pages never render blank due to missing `default` exports in React.lazy chunks:

1. **Page Component Export**:
   Always export as a named function (`export function FooPage() { ... }`).
   Optionally also provide a default export (`export default FooPage`).

2. **Route Import in `src/App.jsx`**:
   Always map the dynamic import with `.then()`:
   ```js
   const FooPage = lazy(() => import("@/pages/FooPage").then(m => ({ default: m.FooPage })))
   ```

3. **Checklist when adding a new route**:
   - [ ] Page created in `src/pages/` with `export function <Name>Page()`
   - [ ] Imported in `src/App.jsx` via `lazy(() => import(...).then(m => ({ default: m.<Name>Page })))`
   - [ ] Route added inside appropriate `<Route>` group with `<Route path="..." element={<NamePage />} />`
   - [ ] Verified via `pnpm build` and browser hard refresh

## Status Reporting Rules (Agents & Humans)

### Core Rule
**Never claim “zero bugs,” “fully functional,” or “production healthy” from code inspection alone.**

### Allowed claims after code-only review
- "Fixed X in file Y"
- "Routes render; export/import consistent"
- "Build passes"

### Evidence required for stronger claims
| Claim | Evidence required |
|---|---|
| **Auth works** | Smoke test A passed on production URLs |
| **Discover works** | Smoke test B with `DATA_SOURCE=api` |
| **Create works** | Smoke test C with real `result_url` |
| **App healthy** | A + B + C passed in last 24h |

### Report Format
When reporting task completion, summaries, or pull requests, structure your response as:
1. **What changed** (files modified/created)
2. **What was verified** (browser / curl / unit test / none)
3. **What remains unverified** (environments or flows not tested)
4. **P0 next step only** (the immediate next priority action)


