# Discover end-to-end proof

Status: **blocked — no authorized non-production provider key yet.** The harness
is ready; nothing here claims Discover works until evidence files exist in this
folder with `"passed": true`.

`backend/scripts/prove_discover.py` drives a **local** API and the jobs worker
over HTTP, the same way the browser does, against the Neon dev branch `dev-w8`
(never production; it refuses any non-loopback API). It records three
scenarios as JSON evidence here: job status timeline, final status, failure
kind, deadline, credits before/after, and a result summary (counts, platforms,
how many rows have days-active and Meta reach). No secrets are written.

## What Ziad provides

One authorized **non-production** provider key, set in the environment of both
the API and the worker (not in any committed file):

| Provider | Variables | `HELIX_PROOF_PROVIDER` |
|---|---|---|
| Metapi | `METAPI_API_KEY` | `metapi` |
| Adyntel | `ADYNTEL_API_KEY`, `ADYNTEL_EMAIL` | `adyntel` |
| Apify | `APIFY_API_TOKEN`, `APIFY_ENABLED=true` | `apify` |
| Meta Ad Library (official) | `META_ACCESS_TOKEN` | `meta_official` |

## Run

```bash
cd backend
# terminal 1: API (reads backend/.env.local -> dev-w8 as helix_api_login)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# terminal 2: worker (DATABASE_URL = helix_worker_login on dev-w8)
python workers/jobs/worker.py
# terminal 3
export HELIX_PROOF_EMAIL=... HELIX_PROOF_PASSWORD=... HELIX_PROOF_PROVIDER=metapi
python scripts/prove_discover.py --scenario success
python scripts/prove_discover.py --scenario cancel
# restart API and worker with DISCOVER_JOB_DEADLINE_S=20, then:
python scripts/prove_discover.py --scenario timeout
```

Pass criteria: `success` ends `succeeded` with at least one result;
`cancel` ends `cancelled` (credits refunded: `credits_after == credits_before`);
`timeout` ends `timed_out` with the deadline honored.
