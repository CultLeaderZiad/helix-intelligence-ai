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

**Important Note on Render Free Tier:**
The free tier automatically spins down the service after a period of inactivity. As a result, **the first request after idle time will be slow (typically ~30-60 seconds) due to a cold start.** This is expected behavior and not a bug.

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

## Database (Neon)

The FastAPI backend is backed by Neon Postgres. The `plan_trial_default` plan row must exist for full session responses. If missing, the backend returns a graceful minimal session.

The frontend has **no** direct database dependency.
