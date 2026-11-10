-- W8 admin cleanup plan for the live database (Neon `dev`, br-gentle-star-axcrbk22).
-- REVIEWED PLAN ONLY. NOT RUN. Run it only with explicit approval, as the owner,
-- AFTER a fresh backup branch, inside one transaction, and read the previews first.
--
-- Why it is needed:
-- * `dev` has 29 users with role = 'admin', most on test domains (example.com,
--   test.com, helix.io, ...).
-- * The W8 admin API's full-admin gate (get_current_full_admin) checks
--   role = 'admin', NOT is_platform_admin. So these accounts keep full admin
--   power even though migration f8b3c4d5e6a7 now promotes only
--   HELIX_PLATFORM_ADMIN_EMAILS.
--
-- Choice made here:
-- * Demote and suspend. Nothing is deleted: their workspaces, jobs, tickets and
--   ledger rows are kept and can be inspected.
-- * Deleting test accounts is a separate, later decision (section 4), because
--   rows in organizations, scrape_jobs, credit_ledger and support tickets
--   reference them.

-- 0. Owner decision (2026-11-10): the ONLY platform admin is cultleaderzoz.dev@gmail.com.
--    Must match HELIX_PLATFORM_ADMIN_EMAILS used when migrating.
CREATE TEMP TABLE keep_admins(email text PRIMARY KEY);
INSERT INTO keep_admins VALUES ('cultleaderzoz.dev@gmail.com');

-- 1. PREVIEW (read-only): who would change.
SELECT u.id, lower(u.email) AS email, u.role, u.is_platform_admin, u.is_suspended, u.created_at
FROM users u
WHERE u.role IN ('admin', 'assistant-admin')
  AND lower(u.email) NOT IN (SELECT email FROM keep_admins)
ORDER BY u.created_at;

SELECT count(*) AS will_demote FROM users
WHERE role IN ('admin', 'assistant-admin') AND lower(email) NOT IN (SELECT email FROM keep_admins);

-- Sanity check: every allowlisted email exists. Expect zero rows.
SELECT k.email AS missing_allowlisted FROM keep_admins k
LEFT JOIN users u ON lower(u.email) = k.email WHERE u.id IS NULL;

-- 2. APPLY (in one transaction). Check the counts before COMMIT.
BEGIN;

UPDATE users
SET role = 'customer', is_platform_admin = false, admin_permissions = '{}'::json
WHERE role IN ('admin', 'assistant-admin')
  AND lower(email) NOT IN (SELECT email FROM keep_admins);

-- Nobody else keeps the platform-admin flag, whatever their role.
UPDATE users SET is_platform_admin = false
WHERE is_platform_admin AND lower(email) NOT IN (SELECT email FROM keep_admins);

-- Test-domain accounts cannot sign in afterwards. Their data is kept.
UPDATE users
SET is_suspended = true
WHERE split_part(lower(email), '@', 2) IN
      ('example.com', 'test.com', 'helixtest.com', 'helix-test.dev', 't.com', 'testrun.io')
  AND lower(email) NOT IN (SELECT email FROM keep_admins);

-- The allowlisted owner is the platform admin.
UPDATE users SET role = 'admin', is_platform_admin = true
WHERE lower(email) IN (SELECT email FROM keep_admins);

-- Verify. Expect exactly 1 row with role = 'admin' and 1 with is_platform_admin.
SELECT role, is_platform_admin, count(*) FROM users GROUP BY 1, 2 ORDER BY 1, 2;
SELECT count(*) FILTER (WHERE role = 'admin') AS admins,
       count(*) FILTER (WHERE is_platform_admin) AS platform_admins
FROM users;

-- COMMIT;   -- uncomment after reviewing the verification output
ROLLBACK;    -- default: nothing changes

-- 3. Rollback after COMMIT: restore from the pre-cleanup backup branch, or
--    re-promote specific users by id.

-- 4. LATER (separate approval): delete suspended test accounts. Inventory the
--    rows that reference each user first (organizations.owner_id,
--    organization_members, scrape_jobs, credit ledger, support_tickets,
--    notifications) and decide cascade versus keep. Not part of the W8 release.
