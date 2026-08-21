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

All secrets (like `DATABASE_URL`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `SCRAPEGRAPH_API_KEY`, `JWT_SECRET`) are read securely from the environment. They should be set in a `.env.local` file for local development and in the deployment dashboard for production.

## Deployment (Render)

We are using **Render (free tier)** as our backend compute target. The configuration is defined in the `render.yaml` file at the root of the repository.

**Important Note on Render Free Tier:**
The free tier automatically spins down the service after a period of inactivity. As a result, **the first request after idle time will be slow (typically ~30-60 seconds) due to a cold start.** This is expected behavior and not a bug.

## Database (Neon)

The FastAPI backend is designed to be backed by Neon Postgres. The frontend has no direct database dependency.
