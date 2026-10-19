# Helix Scout · Lead Generation — Scrapling worker

Engine: `scrapling_engine` — the ONLY public-web lead engine for Lead Generation.
Social/Atlas (`helix_scout`) is untouched by this worker.

## What it does

1. Polls `leadgen_jobs` for `queued` jobs (DB claim, `FOR UPDATE SKIP LOCKED`).
2. Runs the 9-stage pipeline (`app/services/leadgen_pipeline.py`):
   brief → seed → discover → fetch → extract → enrich → score → outreach → export.
3. Heartbeats to `POST /api/v1/scout/leadgen/worker/heartbeat` every 30s so
   `GET /worker/health` reports truthful online/offline.
4. Serves `GET :8091/health` for optional `SCRAPLING_WORKER_URL` pings.

The FastAPI process never imports Scrapling — **only this worker does** — so
the API boots without browsers installed.

## Install (host dev)

```bash
cd backend
pip install -r requirements.txt
pip install -r workers/scrapling/requirements.txt   # scrapling[fetchers]
scrapling install                                   # browsers for stealth/dynamic
export SCRAPLING_WORKER_ENABLED=true
export SCRAPLING_INLINE_WORKER=false                # worker claims, API just enqueues
export DATABASE_URL=... SECRET_KEY=... HELIX_API_BASE_URL=https://<api>/api
python workers/scrapling/worker.py
```

## Docker (preferred)

```bash
cd backend
docker build -f workers/scrapling/Dockerfile -t helix-leadgen-worker .
docker run --env-file .env helix-leadgen-worker
```

Official image base: `ghcr.io/d4vinci/scrapling:latest`
(configurable via `SCRAPLING_DOCKER_IMAGE` — the Dockerfile ARG must match).

## Rules baked in

- `robots_txt_obey` default ON; disabling requires the explicit job flag and
  writes `> audit · robots_obey=false · user=… · job=…` into job logs.
- No fabricated contacts: missing fields stay empty with `extract_status`.
- Outreach is drafted only when `score >= outreach_min_score` AND a real
  email/phone exists — **never auto-sent**.
- BSD-3 attribution for Scrapling: see `NOTICE`.

## Diagnostics and error handling

Application events use the existing Python logging transport with structured
`event`, `request_id`, `tenant_id`, `actor_id`, `job_id`, and `error_type` fields.
Unavailable context is left empty; no external error-reporting service is
claimed. Configure your log collector to retain those structured fields.
Request/response bodies, exception messages/tracebacks, emails, provider keys,
cookies and target URLs are deliberately excluded from these events.
HTTP responses include a server-generated `X-Request-ID` for correlation.

The optional health presence diagnostics require `HEALTH_DIAGNOSTIC_KEY` via
`X-Admin-Secret`. This dedicated credential must differ from `SECRET_KEY`;
the JWT signing key no longer authorizes diagnostics. Without a dedicated key,
only the public health/readiness state is returned.

`helix-audit/probes/runtime-probes.py` is import-safe and refuses execution
unless `HELIX_ALLOW_DISPOSABLE_PROBES=yes`, `ENVIRONMENT=test`, and
`DATABASE_URL` identifies an empty local PostgreSQL database named
`helix_w4_probe_*` (no query overrides). Create a new database explicitly;
never reuse a shared or production database. The script refuses existing
tables and leaves its synthetic fixture for inspection. Its `create_all`
fixture tests application access only: it is **not migration, RLS, or
production deployment evidence** and makes no paid provider requests.
