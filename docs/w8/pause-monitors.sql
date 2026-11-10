-- Pause overdue monitors on the live database (Neon `dev`, br-gentle-star-axcrbk22)
-- BEFORE the W8 embedded worker starts.
-- REVIEWED PLAN ONLY. NOT RUN.
-- Run as the owner, AFTER the pre-w8 backup branch, inside one transaction.
-- No DELETE. This file ends in ROLLBACK. Uncomment COMMIT only when the
-- preview is exactly the 3 overdue daily monitors.
--
-- Why: claim_due_monitors (backend/app/services/monitor_service.py) updates
-- rows where status = 'active' AND next_run_at IS NOT NULL AND next_run_at <= now().
-- The embedded scheduler calls tick() as soon as the loop starts
-- (monitor_scheduler_loop in backend/app/services/job_runner.py).
-- On 2026-11-10 the live branch had 3 active daily monitors, overdue since
-- September. The cutover rehearsal ran 2 of them immediately, about 30 Metapi
-- records each. That is more than the remaining free quota if all 3 run.
--
-- The /monitors Pause button only updates the signed-in workspace. Use this
-- SQL unless those 3 rows are already known to be in that one workspace.
-- next_run_at is left unchanged. Resuming later would make them due at once;
-- push next_run_at forward before a resume if that immediate run is not wanted.

-- 1. PREVIEW. Expect exactly 3 rows, each cadence = 'daily', each next_run_at in the past.
SELECT id, org_id, user_id, name, cadence, status, next_run_at, last_run_at
FROM monitors
WHERE status = 'active'
  AND next_run_at IS NOT NULL
  AND next_run_at <= now()
ORDER BY next_run_at;

SELECT count(*) AS overdue_active,
       count(*) FILTER (WHERE cadence = 'daily') AS overdue_daily
FROM monitors
WHERE status = 'active'
  AND next_run_at IS NOT NULL
  AND next_run_at <= now();

-- 2. APPLY. Stop if the set is not those 3 daily rows.
BEGIN;

DO $$
DECLARE
  n int;
  n_daily int;
BEGIN
  SELECT count(*), count(*) FILTER (WHERE cadence = 'daily')
    INTO n, n_daily
  FROM monitors
  WHERE status = 'active'
    AND next_run_at IS NOT NULL
    AND next_run_at <= now();
  IF n <> 3 OR n_daily <> 3 THEN
    RAISE EXCEPTION 'expected 3 overdue active daily monitors, found % (% daily)', n, n_daily;
  END IF;
END $$;

UPDATE monitors
SET status = 'paused',
    paused_reason = 'Paused for the W8 cutover so the embedded worker does not run overdue monitors.',
    updated_at = now()
WHERE status = 'active'
  AND next_run_at IS NOT NULL
  AND next_run_at <= now();

-- Expect 0 still due, and 3 paused for this reason.
SELECT count(*) AS still_due
FROM monitors
WHERE status = 'active'
  AND next_run_at IS NOT NULL
  AND next_run_at <= now();

SELECT count(*) AS paused_for_cutover
FROM monitors
WHERE status = 'paused'
  AND paused_reason = 'Paused for the W8 cutover so the embedded worker does not run overdue monitors.';

DO $$
DECLARE
  still_due int;
  paused_n int;
BEGIN
  SELECT count(*) INTO still_due
  FROM monitors
  WHERE status = 'active'
    AND next_run_at IS NOT NULL
    AND next_run_at <= now();
  SELECT count(*) INTO paused_n
  FROM monitors
  WHERE status = 'paused'
    AND paused_reason = 'Paused for the W8 cutover so the embedded worker does not run overdue monitors.';
  IF still_due <> 0 OR paused_n <> 3 THEN
    RAISE EXCEPTION 'pause verification failed: still_due=%, paused_for_cutover=%', still_due, paused_n;
  END IF;
END $$;

-- COMMIT;   -- uncomment only after both DO blocks succeed and the preview was the 3 daily rows
ROLLBACK;    -- default: nothing changes

-- 3. After COMMIT, re-read outside the transaction. Do not deploy
--    EMBEDDED_WORKER_ENABLED=true while this returns any row:
-- SELECT id, name, cadence, status, next_run_at
-- FROM monitors
-- WHERE status = 'active' AND next_run_at IS NOT NULL AND next_run_at <= now();
