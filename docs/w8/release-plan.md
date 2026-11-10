# W8 release plan: free-plan cutover runbook, compatibility and rollback

Status: **draft, not approved.** Nothing here has been run on production.

## 0. Facts this plan is built on (verified 2026-11-10)

| Thing | Value |
|---|---|
| Production database | Neon branch **`dev`**, `br-gentle-star-axcrbk22`, endpoint `ep-cold-rice-axydlqmv` (us-east-2). Proven server-side (`current_setting('neon.branch_id')`) with the `DATABASE_URL` from Render's environment export. |
| Its state | Revision `b1c2d3e4f5a6`, 230 users, 197 workspaces, **no `helix_*` roles**, Render connects as `neondb_owner` (BYPASSRLS). 29 users have `role='admin'`, most on test domains. |
| The branch named `production` | `br-soft-mode-ax44ab32`: an empty leftover (1 user). **Not used.** Earlier backups and rehearsals that targeted it were based on its name, not on evidence; they don't protect the live data. |
| Render | `srv-da3ocem7bikc73bfi4fg`, ohio, **free** web service, not Blueprint-managed. No pre-deploy command, no Shell/SSH, `healthCheckPath` empty, rollback only to the last 2 deploys. |
| Migrations to apply | **22**: `b1c2d3e4f5a6` → `c9e1f3a5b7d0` (rows 5–26 of `release-checklist.md`). |
| Release candidate | `fix/core-W8` (draft PR 31). CI must be green on the exact commit merged. |

## 1. Compatibility evidence (rehearsed on fresh copies of `dev`)

- All 22 migrations apply in one run. Row counts are unchanged except 2 workspace-less patterns moved to `pattern_quarantine`. `alembic check` is clean, thanks to the reconciliation migration `c9e1f3a5b7d0`.
- **Old backend (`main` @ `5b45806`) on the migrated copy, as the owner:** health, sign-up and sign-in, session and all main reads returned 200, as did creating a search, a ticket and a monitor. So the database can be migrated while the old API keeps serving, and a code rollback can keep the migrated database.
- **The old backend must keep the owner `DATABASE_URL`.** It doesn't set the tenant settings that row-level security needs, so with `helix_api_login` its queries would see no rows (fail-closed).
- **The new backend refuses the owner role in production** (`assert_rls_role`). Therefore the switch of `DATABASE_URL` happens together with the code deploy, and rollback restores the owner URL.
- **Full runbook rehearsal** on `w8-cutover-rehearsal`: see section 6.

## 2. Before the day

1. CI green on the release commit.
2. Rotate the secrets listed in `docs/w8/secret-rotation.md`. Do Neon, `SECRET_KEY` and Metapi at the cutover itself.
3. **Existing monitors:** the live branch has 3 active daily monitors. Once the embedded worker
   runs, they run every day (up to about 30 Metapi records each). Pause them in Admin, or accept
   the cost, before step 9.
4. Decide on `docs/w8/admin-cleanup.sql`: it demotes and suspends test admins, and is reviewed but not run.
5. Generate locally, and keep only in a password manager:
   - the `helix_api_login` password;
   - `CREDENTIAL_ENCRYPTION_KEY`, different from `SECRET_KEY`.
6. Render → helix-backend → Settings:
   - **Auto-Deploy: Off**
   - **Health Check Path: `/api/health`**
7. Vercel: plan to promote the frontend only after the backend is healthy. Either use the "Instant Rollback" / promote flow, or pause production auto-deploys for the merge.

## 3. Cutover (about 30 minutes, low-traffic time)

1. **Freeze.** No admin changes. Note T0 (UTC).
2. **Backup branch** of the live branch at T0 (instant, copy-on-write):
   `neon branches create --project-id quiet-dawn-26282927 --parent br-gentle-star-axcrbk22 --name pre-w8-<YYYYMMDD-HHMM>`
   Also note the plan's point-in-time restore window as a second safety net.
3. **Migrate from your machine, not Render.** Use the owner URL on the **direct** host (no `-pooler`), copied from the Neon console, held only in your shell.

   ```bash
   cd backend
   export TEST_DATABASE_URL='<owner direct URL, never saved>'
   export HELIX_PLATFORM_ADMIN_EMAILS='cultleaderzoz.dev@gmail.com'
   python -m alembic upgrade head
   python -m alembic check      # must print: No new upgrade operations detected.
   ```

   The old API keeps serving throughout. Its writes land in the migrated schema (section 1).
4. **Login role, created by SQL as the owner** (not `neon roles create`, which adds the role to `neon_superuser`):

   ```sql
   CREATE ROLE helix_api_login LOGIN PASSWORD '<generated>' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS INHERIT;
   GRANT helix_app TO helix_api_login;
   GRANT helix_worker TO helix_api_login;   -- embedded worker (free plan)
   ```

   Check: `select rolbypassrls from pg_roles where rolname='helix_api_login'` must be false.
5. **Admin cleanup** (`admin-cleanup.sql`), only if approved. Review the previews, then COMMIT.
6. **Merge PR 31 into `main`.** Auto-deploy is off, so nothing deploys yet.
7. **Render env.** Use Environment → Edit → **Save only**, without a deploy. Keep the old owner `DATABASE_URL` in the password manager for rollback.
   - Set:
     - `ENVIRONMENT=production`
     - `PUBLIC_APP_BASE_URL` and `APP_BASE_URL` (the Vercel URL)
     - `BACKEND_CORS_ORIGINS`: Vercel origin(s) only
     - `CREDENTIAL_ENCRYPTION_KEY`
     - `RESEND_API_KEY` and `RESEND_FROM`
     - `EMBEDDED_WORKER_ENABLED=true`
     - `HELIX_DISPATCH_INLINE=false`
     - `METAPI_MONTHLY_RECORD_BUDGET` (the remaining records)
     - `DATABASE_URL`: `helix_api_login` on the **pooled** host of the live branch
   - Do steps 7–9 back to back. A free instance that restarts in between would boot the old code with the new `DATABASE_URL`, and fail closed.
8. **Verify config without a shell:** Export → Download .env, then run `python scripts/check_release_env.py --env-file <file>`. Every line must be `OK`. Delete the exported file afterwards.
9. **Deploy:** Render → Manual Deploy → *Deploy latest commit*. With the health check set, Render switches traffic only when `/api/health` answers.
10. **Frontend:** promote the matching Vercel production deployment.
11. **Verify:**
    - `/api/health`
    - sign in as the admin
    - `/api/public/pricing`
    - one search (≤ 15 Metapi records) finishes through the embedded worker
    - admin Organizations and Pricing pages
12. **Unfreeze.** Remove the downloaded env file.

## 4. Rollback

**Code problem** (most likely):
1. Render env (Save only): restore the **owner `DATABASE_URL`**. Remove or reset `ENVIRONMENT`, `EMBEDDED_WORKER_ENABLED` and the other new keys if the old code objects.
2. Render → Rollback to the previous deploy (`5b45806`). Free plans keep only the last 2 deploys, so don't deploy anything else in between.
3. Vercel → Instant Rollback.
4. **Keep the migrated database.** The old code runs on it, so every write since T0 stays.

**Migration fails at step 3:** each migration is transactional. The database stays at the last good revision and the old code keeps working. Fix forward, or restore.

**Data corruption (last resort):**
1. Put the app in maintenance (`DISCOVER_ENABLED=false`, freeze admin).
2. Export rows created after T0 from `users`, `organizations`, `scrape_jobs`, `support_tickets` and `saved_creatives` (`created_at > T0`).
3. Restore the live branch from `pre-w8-…` (Neon "Restore" to the backup branch, or to a timestamp).
4. Re-insert the exported rows.
5. Restore the owner `DATABASE_URL` and roll back the code.

Down-migrations are **not** a rollback path: some W8 migrations quarantine or backfill data.

## 5. Free worker limits

See `docs/w8/free-worker.md`. In short:
- The service sleeps after about 15 minutes idle, and queued work waits for the next request.
- Scheduled monitors run only while it's awake; missed runs are not backfilled.
- A wake-up ping makes runs likely, not guaranteed.
- A job interrupted by spin-down is rerun after 120 s.

## 6. Rehearsal record

End-to-end run on `w8-cutover-rehearsal` (`br-bitter-boat-axjl0hax`, a fresh copy of `dev`),
2026-11-10. Steps 3.3–3.4 and 3.9–3.11 were run locally, with the same commands and roles as above:

| Step | Result |
|---|---|
| Before | revision `b1c2d3e4f5a6`, 230 users, 197 workspaces, 177 searches, 56 patterns |
| Migrate (owner, direct host, `HELIX_PLATFORM_ADMIN_EMAILS` = the owner's email) | 22 migrations applied, `b1c2d3e4f5a6` → `c9e1f3a5b7d0`, exit 0 |
| `alembic check` | "No new upgrade operations detected." |
| Platform admins | 1 (the allowlisted email); the other 28 `role='admin'` rows were **not** promoted |
| `CREATE ROLE helix_api_login ...` + grants | superuser false, bypassrls false, member of `helix_app` and `helix_worker`, **not** in `neon_superuser` |
| New API, `ENVIRONMENT=production`, `EMBEDDED_WORKER_ENABLED=true`, as `helix_api_login` | started (no "Refusing"), health 200, no tracebacks |
| Sign-up / sign-in | 202 / 200, 7-day trial granted |
| Search through the embedded worker, all provider keys blank | queued → finalized `failed: provider_outage` (expected with no provider), credits refunded |
| Existing monitors | the embedded scheduler ran 2 of the 3 active daily monitors immediately |
| After | users 230 → 231, workspaces 197 → 198 (the test sign-up); patterns 56 → 54 plus 2 in `pattern_quarantine`; no other existing table lost rows |

