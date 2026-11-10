-- W8 admin cleanup plan for the live database (Neon `dev`, br-gentle-star-axcrbk22).
-- REVIEWED PLAN ONLY. NOT RUN. Run it only with explicit approval, as the owner,
-- AFTER a fresh backup branch, inside one transaction, and read the previews first.
--
-- Why it is needed:
-- * `dev` has 29 users with role = 'admin', most on test domains.
-- * The W8 admin API's full-admin gate (get_current_full_admin) checks
--   role = 'admin', NOT is_platform_admin. So these accounts keep full admin
--   power even though migration f8b3c4d5e6a7 now promotes only
--   HELIX_PLATFORM_ADMIN_EMAILS.
--
-- Choice made here:
-- * Demote and suspend. Nothing is deleted: their workspaces, jobs, tickets and
--   ledger rows are kept and can be inspected. This file has no DELETE.
-- * Deleting test accounts is a separate, later decision (section 4), because
--   rows in organizations, scrape_jobs, credit_ledger and support tickets
--   reference them.
--
-- Suspend domains:
-- * Approved by Ziad, rehearsed on a copy of dev (2026-11-10): example.com,
--   test.com, helixtest.com, helix-test.dev, t.com, testrun.io.
--   That run suspended 191 of 231 accounts, left exactly one admin
--   (cultleaderzoz.dev@gmail.com, also the only platform admin), and deleted
--   nobody. The other 28 ex-admins got 403 on every admin route tested.
-- * Added after that rehearsal, not part of the 191 count: helix.io, helix.ai,
--   helix.com, vynex.com, vhynex.com.
-- * Never suspend cultleaderzoz.dev@gmail.com or any @gmail.com account.
--   gmail.com is not in the domain list, and the UPDATE excludes it anyway.

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

-- Who the suspend list would catch. gmail.com must not appear.
SELECT split_part(lower(email), '@', 2) AS domain, count(*) AS accounts
FROM users
WHERE split_part(lower(email), '@', 2) IN (
      'example.com', 'test.com', 'helixtest.com', 'helix-test.dev', 't.com', 'testrun.io',
      'helix.io', 'helix.ai', 'helix.com', 'vynex.com', 'vhynex.com')
GROUP BY 1
ORDER BY 1;

-- 2. APPLY (in one transaction). Check the counts before COMMIT.
BEGIN;

-- gmail.com accounts that are not suspended yet. The UPDATEs below must leave them that way.
CREATE TEMP TABLE gmail_not_suspended AS
SELECT id FROM users
WHERE split_part(lower(email), '@', 2) = 'gmail.com'
  AND NOT COALESCE(is_suspended, false);

UPDATE users
SET role = 'customer', is_platform_admin = false, admin_permissions = '{}'::json
WHERE role IN ('admin', 'assistant-admin')
  AND lower(email) NOT IN (SELECT email FROM keep_admins);

-- Nobody else keeps the platform-admin flag, whatever their role.
UPDATE users SET is_platform_admin = false
WHERE is_platform_admin AND lower(email) NOT IN (SELECT email FROM keep_admins);

-- Test-domain accounts cannot sign in afterwards. Their data is kept.
-- gmail.com is excluded even though it is not in the list.
UPDATE users
SET is_suspended = true
WHERE split_part(lower(email), '@', 2) IN (
      'example.com', 'test.com', 'helixtest.com', 'helix-test.dev', 't.com', 'testrun.io',
      'helix.io', 'helix.ai', 'helix.com', 'vynex.com', 'vhynex.com')
  AND split_part(lower(email), '@', 2) <> 'gmail.com'
  AND lower(email) <> 'cultleaderzoz.dev@gmail.com'
  AND lower(email) NOT IN (SELECT email FROM keep_admins);

-- The allowlisted owner is the platform admin.
UPDATE users SET role = 'admin', is_platform_admin = true
WHERE lower(email) IN (SELECT email FROM keep_admins);

-- Verify. Expect exactly 1 admin and 1 platform admin, the same person, not suspended.
SELECT role, is_platform_admin, count(*) FROM users GROUP BY 1, 2 ORDER BY 1, 2;
SELECT count(*) FILTER (WHERE role = 'admin') AS admins,
       count(*) FILTER (WHERE is_platform_admin) AS platform_admins
FROM users;

SELECT lower(email) AS email, role, is_platform_admin, is_suspended
FROM users
WHERE lower(email) = 'cultleaderzoz.dev@gmail.com';
-- Expect: role admin, is_platform_admin true, is_suspended false.

-- Expect 0. This script must not suspend a gmail.com account that was active.
SELECT count(*) AS gmail_newly_suspended
FROM users u
JOIN gmail_not_suspended g ON g.id = u.id
WHERE u.is_suspended;

-- Expect 0 rows: no gmail.com address is in the suspend domain list.
SELECT id, lower(email) AS email
FROM users
WHERE is_suspended
  AND split_part(lower(email), '@', 2) = 'gmail.com'
  AND id IN (SELECT id FROM gmail_not_suspended);

-- Abort unless the owner is the only admin and no active gmail.com account was suspended.
-- A failed check leaves the transaction aborted, so COMMIT cannot apply it.
DO $$
DECLARE
  admin_n int;
  platform_n int;
  gmail_n int;
  owner_ok boolean;
BEGIN
  SELECT count(*) FILTER (WHERE role = 'admin'),
         count(*) FILTER (WHERE is_platform_admin)
    INTO admin_n, platform_n
  FROM users;
  SELECT count(*) INTO gmail_n
  FROM users u
  JOIN gmail_not_suspended g ON g.id = u.id
  WHERE u.is_suspended;
  SELECT EXISTS (
    SELECT 1 FROM users
    WHERE lower(email) = 'cultleaderzoz.dev@gmail.com'
      AND role = 'admin'
      AND is_platform_admin IS TRUE
      AND COALESCE(is_suspended, false) IS FALSE
  ) INTO owner_ok;
  IF admin_n <> 1 OR platform_n <> 1 OR gmail_n <> 0 OR NOT owner_ok THEN
    RAISE EXCEPTION
      'admin cleanup verification failed: admins=%, platform_admins=%, gmail_newly_suspended=%, owner_ok=%',
      admin_n, platform_n, gmail_n, owner_ok;
  END IF;
END $$;

-- COMMIT;   -- uncomment after the verification output and the DO block both succeed
ROLLBACK;    -- default: nothing changes

-- 3. Rollback after COMMIT: restore from the pre-cleanup backup branch, or
--    re-promote specific users by id.

-- 4. LATER (separate approval): delete suspended test accounts. Inventory the
--    rows that reference each user first (organizations.owner_id,
--    organization_members, scrape_jobs, credit ledger, support_tickets,
--    notifications) and decide cascade versus keep. Not part of the W8 release.
