# Helix jobs worker

Runs the durable background work that must not live in the web process:

1. Claims rows from the Postgres `work_items` outbox (`FOR UPDATE SKIP LOCKED`)
   and executes them with lease renewal, heartbeats and owner/generation
   fencing (`app/services/work_outbox.py`). Kinds: `discover` (searches) and
   `monitor` (scheduled competitor watches).
2. Sweeps stale jobs at startup and every 60 s (`app/services/job_reconciliation.py`),
   refunding interrupted Discover jobs.

It uses the same Python dependencies as the API. There is no browser and no
scraping framework in this image (Scout and Lead Generation were removed in W8).

## Run

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL=...   # helix_worker_login, never the owner role
export SECRET_KEY=...     # same value as the API
python workers/jobs/worker.py
```

Docker (build from `backend/`):

```bash
docker build -f workers/jobs/Dockerfile -t helix-jobs-worker .
docker run --env-file .env helix-jobs-worker
```

On Render this is a Background Worker using `backend/workers/jobs/Dockerfile`.
The worker refuses to start if its database role is a superuser or bypasses
RLS.

## Diagnostics

Application events use the existing structured logging (`event`, `request_id`,
`tenant_id`, `actor_id`, `job_id`, `error_type`). Request bodies, exception
messages, emails, provider keys and target URLs are excluded.

The optional health presence diagnostics on the API require
`HEALTH_DIAGNOSTIC_KEY` via `X-Admin-Secret`.

`backend/scripts/runtime-probes.py` is import-safe and refuses execution
unless `HELIX_ALLOW_DISPOSABLE_PROBES=yes`, `ENVIRONMENT=test`, and
`DATABASE_URL` identifies an empty local PostgreSQL database named
`helix_w4_probe_*`. It is not migration, RLS or production evidence and makes
no paid provider requests.
