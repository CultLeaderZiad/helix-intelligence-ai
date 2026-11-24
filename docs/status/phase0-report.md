# Phase 0 report (2026-11-24)

Branch `claude/app-features-improvements-gjkvnh`, Postgres 16 local, no provider keys, production not reachable from this sandbox
(the egress proxy returns 403 for `onrender.com`). Nothing in this file was run against production.

## What was run

| Check | Result | Status |
|---|---|---|
| `pnpm install --frozen-lockfile` | ok | Verified |
| `pnpm lint` (max-warnings 0) | clean | Verified |
| `pnpm typecheck` | clean | Verified |
| `pnpm test` | node: 5/5, vitest: 55 files, 250/250 | Verified |
| `pnpm build` | built in ~5 s | Verified |
| backend `compileall` | ok | Verified |
| `alembic upgrade head` + `alembic check` | applied all, "No new upgrade operations detected" | Verified |
| backend `pytest -W error` | 675 passed, 9 skipped | Verified |

The 9 skips are the W4 migration/transaction tests. They need `W4_DISPOSABLE_DATABASE_URL`, which CI sets and this run did not. Not a code problem, but those 9 were not run here.

## Suspected problems

| # | Suspicion | Finding | Status |
|---|---|---|---|
| 1 | Monitors may never run in production | Dispatch paths: external `POST /api/monitors/tick` (`CRON_SECRET`), or the in-worker loop `monitor_scheduler_loop` (`job_runner.py:51`, every `MONITOR_SCHEDULER_INTERVAL_S`, default 300 s). `EMBEDDED_WORKER_ENABLED` defaults to `false` and `render.yaml` does not set it. **Owner-supplied `/api/health` (2026-11-24): `worker.mode=embedded`, `running=true`, `last_poll_seconds_ago=1`; `migration.up_to_date=true` at `c6e8a0b2d4f7` (= code head).** So the embedded scheduler is on. Still unknown: `MONITOR_SCHEDULER_INTERVAL_S` in the dashboard (0 disables it), and whether a monitor has actually completed a run there. | Worker **Verified** (owner output, not run by me). Monitor run end to end: Unverified |
| 2 | Run dies when Render sleeps | Runs are `asyncio.create_task` in the process (`monitor_service.py` ~494/533). Recovery relies on the job heartbeat and `job_reconciliation.py`; this was read, not crash-tested. A run left `running` blocks a manual run with 409 (`monitor_service.py:508-514`). | Unverified (needs a kill-and-restart test) |
| 3 | False "ad stopped" events | Empty scrape is guarded: `diff_run` returns `skipped_reason="empty_result"` (`creative_fingerprint.py:253`). Single absence is guarded by `MONITOR_MISS_THRESHOLD` (default 2). **There is no guard for a partial scrape**: if a provider returns 30% of the ads on two runs in a row, every missing ad becomes `killed_ad`. | **Gap confirmed by code reading.** No test written yet. |
| 4 | Discover never run against a real provider | No provider key in this environment. | Unverified (unchanged since W8) |
| 5 | Rate limits in memory | `app/middleware/rate_limit.py:248` (`_BUCKETS`) and `app/core/limits.py:27` (`_HITS`) are process-local dicts. Used by `main.py`, `account`, `monitors`, `boards`, `support`, `discover` routers. Resets on restart, not shared across instances. | Confirmed |
| 6 | Meta official API and commercial ads | Not testable here. Based on Meta's documented scope. Any stable ad ID has to come from a provider field. | Unverified, check with a real provider response |
| 7 | Free LLM providers | `ai_router.py` / `call_policy.py` not yet read in depth. | Not done |

## Other findings
- `.env.live` and `.env.production` are tracked in git. They hold only public URLs and an email, no secrets (values checked).
- `DEVELOPMENT.md` is correct that Neon branch `dev` (`br-gentle-star-axcrbk22`) is what Render uses; confirmed by the owner from the Render and Neon dashboards.

## P0 next step
Phase 1: make the monitor survive the Render free-tier sleep (the worker only runs while the instance is awake; keepalive is a GitHub cron every 10 min and is best effort), add the partial-scrape guard, and prove one full monitor run.
