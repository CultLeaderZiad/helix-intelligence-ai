# Helix state machines (W8 inventory)

Every status column and status-like UI value in Helix, what moves it, and what
is now enforced. The executable source of truth for the server-side machines is
[`backend/app/core/state_machines.py`](../../backend/app/core/state_machines.py);
`catalog()` / `catalog_markdown()` render it for API, Markdown and MCP surfaces.
Tests: `backend/tests/test_state_machines_w8.py` (every ordered pair of every
machine, legal and illegal) and `src/lib/__tests__/jobStatus.w8.test.js`.

No stored value, API field or migration changed. Guards raise
`IllegalTransition` (a `ValueError`) only on moves the code never made before.

## Summary

| Machine | Stored in | States | Terminal | Enforced now |
|---|---|---|---|---|
| Discover job | `scrape_jobs.status` (+ `stage`) | queued, running, succeeded, failed, cancelled, timed_out | last four | `_set_discovery_terminal`, retry requeue |
| Work item | `work_items.status` | queued, leased, running, succeeded, dead, canceled | succeeded, dead, canceled | `finish_work_item` |
| Monitor | `monitors.status` | active, paused | none | table only (API already limits to these two) |
| Monitor run | `monitor_runs.status` | running, succeeded, failed, skipped | all but running | table only |
| Credit reservation | `credit_reservations.status` | pending, settled, refunded | refunded | `settle_reservation` |
| Support ticket | `support_tickets.status` | open, in_progress, resolved | none | status list shared with `update_ticket_status` |
| Access | derived by `billing_service._access_state` | pending, approved, rejected, expired, revoked | none | table + test that outputs stay inside it |
| Board share link | derived in `board_share_service` | active, expired, revoked | expired, revoked | table only |
| Workspace / trial | `organizations.status`, `users.trial_expires_at` | active, trial_expired, quota_exhausted, daily_limit_reached, suspended | none | not tabled (see follow-ups) |
| Discover UI phase | `useDiscoverySearch` `PHASE` | idle, submitting, running, fetching_results, ready, error, cancelling, cancel_error, cancelled, timed_out | — | terminal set now shared via `@/lib/constants` |
| Auth session | `AuthContext` `AUTH_STATUS` | loading, authenticated, unauthenticated | — | already an explicit enum |
| Onboarding / tour | `OnboardingWizardModal`, `OnboardingTour` (localStorage flags) | not started, in progress, done, restart requested | — | unchanged |

## Discover job (`scrape_jobs.status`)

```
(create) ──inline──▶ running
(create) ──────────▶ queued ──lease──▶ running ──▶ succeeded
                      │  ▲               │  └────▶ failed | cancelled | timed_out
                      │  └─retryable─────┘
                      └──▶ succeeded | failed | cancelled | timed_out
```

`queued → succeeded` is legal: after a crash reclaim the job is queued again
and the replacement worker can finish it without re-marking it running.

- **Triggers.** User: create (`POST /discover`), cancel. Worker: lease → running,
  provider retry → queued, finish. Read path: `get_job` times out an overdue
  queued/running job. Reaper: `job_reconciliation` (raw SQL) marks orphans
  failed / timed_out, filtered by `status IN ('queued','running')`.
- **Stages** (`stage`): queued, init, scoring, complete, zero_results, and the
  terminal status itself. Stage is presentation only; it is not guarded.
- **Refunds.** Every non-success terminal refunds the job's reservation (see
  credit reservations). `succeeded` with zero rows is still `succeeded`.
- **Guards.** `_lock_active_discovery_job` already refused non-active rows;
  `_set_discovery_terminal` now also checks the table, so a second finish of a
  finished job raises instead of overwriting.
- **Findings.**
  - Raw-SQL reconciliation bypasses the Python table; it is safe only because of
    its `WHERE status IN (...)` filters. Keep those filters in sync with
    `SCRAPE_JOB_ACTIVE`.
  - The admin Scrape Jobs filter offers all/running/succeeded/failed/queued but
    not cancelled or timed_out.

## Work item (`work_items.status`)

```
queued ──claim──▶ leased ──start──▶ running ──▶ succeeded
  │                 │  └─lease expired─▶ queued | dead | canceled
  └─cancel─▶ canceled   └─cancel_requested─▶ canceled
                    running ──retryable──▶ queued (backoff) | dead (attempt cap)
```

- Triggers: `claim_next`, `execute_work_item`, `finish_work_item`,
  `defer_or_dead`, `requeue_expired_leases` (reaper), `request_cancel` and
  `discover_service.cancel_job` (user).
- **Finding: duplicated spelling.** Work items store `canceled`; scrape jobs
  store `cancelled`. Both are persisted and covered by DB check constraints, so
  neither is renamed. The frontend accepts both (`isJobCancelled`).
- **Finding: unguarded finish.** `finish_work_item(owner=None)` could write any
  status from any state. It now goes through `WORK_ITEM.check`.

## Monitor and monitor run

- Monitor: `active ⇄ paused`. User toggles via `update_monitor` (plan limits
  checked on activation; activation clears `paused_reason` and
  `consecutive_failures`). System pauses on `MONITOR_MAX_FAILURES` consecutive
  failed runs, on quota exhaustion, and when the owner no longer exists.
  **Finding:** the pause cause lives only in free-text `paused_reason`; there is
  no machine-readable pause code for agents.
- Run: created `running` (or directly `skipped` when one is in flight) →
  `succeeded | failed`. The reconciler fails runs stuck in `running`.

## Credit reservation

`pending → settled → refunded`, `pending → refunded`; sync charges are created
`settled`. `refunded` is terminal and idempotent: duplicate refunds are logged
and ignored; settling a refunded reservation raised before and still does.

## Support ticket

Create → `open`. Staff reply: `open → in_progress`. Customer reply:
`resolved → open`. Staff may set any of the three via
`PATCH /support/tickets/{id}`. No terminal state; the allowed list is now the
shared `SUPPORT_TICKET_STATUSES`.

## Access (derived) and board share links (derived)

Neither is stored; both are computed when read.

- Access, from the latest grant and request: active grant → `approved`; later
  rejected request → `rejected`; later pending request → `pending`; grant past
  expiry → `expired`; revoked grant → `revoked`; otherwise `pending`. A new
  request after expired/revoked/rejected returns to `pending`.
- Board share: `revoked` if `revoked_at`, else `expired` if past `expires_at`,
  else `active`. Revocation and expiry are one-way.

## Workspace status and the sign-up trial

`organizations.status` takes `active | trial_expired | quota_exhausted |
daily_limit_reached | suspended`. Billing sets `quota_exhausted` when credits
run out and back to `active` on refund or top-up. The 7-day sign-up trial is
`users.trial_expires_at`, set at sign-up when enabled. Not tabled in this pass:
several writers (billing, admin, daily reset) and the trial is a timestamp, not
a status.

## Frontend

- `useDiscoverySearch` `PHASE` mirrors the job plus client-only phases
  (submitting, fetching_results, cancelling, cancel_error). Terminal job
  statuses now come from `JOB_TERMINAL_STATUSES` in `src/lib/constants.js`.
  **Finding:** the hook's `CANCELLING_STATUSES` (`cancelling`,
  `cancel_requested`) are never emitted by the server for scrape jobs; the
  cancelling phase is driven only by the client.
- `AuthContext` already uses an explicit `AUTH_STATUS` enum.
- Onboarding wizard and tour use localStorage flags; no server state to match.

## Follow-ups (not done here)

1. Machine-readable `paused_code` for monitors (needs a migration; wait for the
   release).
2. Table and guard `organizations.status`.
3. Serve `catalog()` from a read-only endpoint / MCP resource.
4. Turn `PHASE` into a reducer with a transition table.
5. Add cancelled / timed_out to the admin Scrape Jobs filter (EN + AR copy).
