# Free worker: the jobs loop inside the API process

Searches (Discover jobs) and monitor runs take 30–150 s, so the API queues
them in `work_items` and a jobs worker runs them. Render's free plan has no
background workers, so W8 can run the same loop **inside the API process**.

## How to turn it on

1. API service environment:
   - `EMBEDDED_WORKER_ENABLED=true`
   - `HELIX_DISPATCH_INLINE=false` (required in production anyway)
2. Database, as the owner, once:
   `GRANT helix_worker TO helix_api_login;`
   - The worker claim policies admit members of `helix_worker` only while the
     loop has set `helix.worker_claim` for its transaction. API request
     handlers never set it.
   - Tenant rows stay under the normal per-workspace RLS.
3. Do not also run the standalone worker against the same database unless you
   want two loops. Two loops are safe, because claims use `SKIP LOCKED` and
   leases are fenced, but they're unnecessary.

Code:
- `app/services/job_runner.py`: the shared loop.
- `app/services/embedded_worker.py`: start/stop from the API lifespan.
- `workers/jobs/worker.py`: the unchanged standalone entry point.

## What is proven

| Behaviour | Proof |
|---|---|
| Job completion | `tests/test_w8_embedded_worker.py`; live on `w8-rehearsal` with the restricted API login and no separate worker: search claimed and finalized |
| Retry after an error | Test: first attempt raises, item requeued with backoff (`attempt_count` 1 → 2), then succeeds |
| Process dies mid-job | Test: loop killed while a job runs; row keeps `running` with the old lease; after the lease expires it is requeued, a new loop finishes it (attempt 2); stale completions from the old lease are fenced |
| API restarted with a queued job | Live: search submitted, API killed, restarted API finished it |
| Monitor scheduling | Test: scheduler ticks inside the loop; live: a new monitor ran within 10 s and got its next run time |

## Limits on a free host (read before relying on it)

Render's free web service **spins down after about 15 minutes without HTTP
traffic** and cold-starts (about 30–60 s) on the next request. The embedded
loop sleeps with it.

- **Queued searches wait while the service sleeps.** In practice a user is on
  the site when they search, so the service is awake. A search queued just
  before spin-down runs when the next request wakes it.
- **Scheduled monitors only run while the service is awake.** A missed monitor
  runs once at the next tick after wake-up. Missed periods are not backfilled.
- **A cron "wake-up" ping does not guarantee execution.**
  - The ping can fail or arrive late.
  - The cold start can exceed the pinger's timeout.
  - The service can spin down again before a long job finishes.
  - Render can restart free instances at any time.

  A ping (Cloudflare Workers cron trigger or cron-job.org hitting
  `/api/health` or `/api/monitors/tick` with `X-Cron-Secret`) only makes
  wake-ups likely.
- **Spin-down mid-job.** The job keeps its lease. After `WORK_LEASE_S` (120 s)
  the next awake loop requeues and reruns it, so provider records for that
  attempt are spent twice. If the job's own deadline passes while asleep,
  reconciliation marks it `timed_out` and refunds the user's credits.
- **Free instance hours.** About 750/month per workspace covers one always-on
  service, not two.

When there are paying users, move the loop to an always-on process: a paid
Render worker, or a small always-free VM. Run the standalone
`workers/jobs/worker.py` there and set `EMBEDDED_WORKER_ENABLED=false`. No
code changes are needed.
