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
| `DATABASE_URL` | ✅ | Neon Postgres connection string |
| `BACKEND_CORS_ORIGINS` | ✅ (prod) | Comma-separated list of allowed frontend origins, e.g. `https://helix-frontend.vercel.app` |
| `GROQ_API_KEY` | optional | Groq inference API |
| `OPENROUTER_API_KEY` | optional | OpenRouter API |
| `GEMINI_API_KEY` | optional | Google Gemini API |
| `SCRAPEGRAPH_API_KEY` | optional | ScrapeGraph API |
| `META_ACCESS_TOKEN` | optional | Meta Marketing API |
| `BRIGHTDATA_API_KEY` | optional | Bright Data API |
| `APIFY_API_TOKEN` | optional | Apify API |

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

## Database (Neon)

The FastAPI backend is designed to be backed by Neon Postgres. The frontend has no direct database dependency.
