# W8 release plan: free-plan cutover runbook, compatibility and rollback

Status: **draft, not approved.** Nothing here has been run on production.

## 0. Facts this plan is built on (verified 2026-11-10)

| Thing | Value |
|---|---|
| Production database | Neon branch **`dev`**, `br-gentle-star-axcrbk22`, endpoint `ep-cold-rice-axydlqmv` (us-east-2). Proven server-side (`current_setting('neon.branch_id')`) with the `DATABASE_URL` from Render's environment export. |
| Its state | Revision `b1c2d3e4f5a6`, 230 users, 197 workspaces, **no `helix_*` roles**, Render connects as `neondb_owner` (BYPASSRLS). 29 users have `role='admin'`, most on test domains. |
| The branch named `production` | `br-soft-mode-ax44ab32`: an empty leftover (1 user). **Not used.** Earlier backups and rehearsals that targeted it were based on its name, not on evidence; they don't protect the live data. |
| Render | Service **`helix-intelligence-ai`** (`srv-da3ocem7bikc73bfi4fg`), ohio, **free** web service, not Blueprint-managed. `render.yaml` used to name it `helix-backend`; that name is wrong and is corrected in the blueprint. No pre-deploy command, no Shell/SSH, `healthCheckPath` empty, rollback only to the last 2 deploys. `main` auto-deploys. |
| Migrations to apply | **22**: `b1c2d3e4f5a6` → `c9e1f3a5b7d0` (rows 5–26 of `release-checklist.md`). |
| Release candidate | `fix/core-W8` (draft PR 31). CI must be green on the exact commit merged. |
| PR 31 base, 2026-11-10 | **`fix/intelligence-W7`**, not `main` (`gh pr view 31`). Retarget to `main` before merging. Merging as it stands does not update `main` and does not deploy. |

## 1. Compatibility evidence (rehearsed on fresh copies of `dev`)

- All 22 migrations apply in one run. Row counts are unchanged except 2 workspace-less patterns moved to `pattern_quarantine`. `alembic check` is clean, thanks to the reconciliation migration `c9e1f3a5b7d0`.
- **Old backend (`main` @ `5b45806`) on the migrated copy, as the owner:** health, sign-up and sign-in, session and all main reads returned 200, as did creating a search, a ticket and a monitor. So the database can be migrated while the old API keeps serving, and a code rollback can keep the migrated database.
- **The old backend must keep the owner `DATABASE_URL`.** It doesn't set the tenant settings that row-level security needs, so with `helix_api_login` its queries would see no rows (fail-closed).
- **The new backend refuses the owner role in production** (`assert_rls_role`). Therefore the switch of `DATABASE_URL` happens together with the code deploy, and rollback restores the owner URL.
- **Full runbook rehearsal** on `w8-cutover-rehearsal`: see section 6.

## 2. Before the day

1. CI green on the release commit.
2. **Retarget PR 31 onto `main`.** Its base is `fix/intelligence-W7` (confirmed 2026-11-10). Change the base to `main`, then read the diff against `main`. Do not merge while the base is `fix/intelligence-W7`. This document does not retarget or merge it.
3. **Turn Auto-Deploy off on `helix-intelligence-ai` before that retarget is merged.** `main` auto-deploys the API. Leave it off through the cutover. The deploy happens only at step 10, with the new env.
4. Rotate the secrets in `docs/w8/secret-rotation.md` **except the Neon owner password**. Reset `neondb_owner` only after the new deploy is healthy (step 12), and keep that **new** owner URL for rollback. Rotate `SECRET_KEY` in the deploy-moment group (step 10), not while `5b45806` is still the running deploy. Provider keys can be rotated before the day; store the new values in a password manager, never in chat.
5. **Monitors.** The live branch has 3 active daily monitors, overdue since September. The embedded worker's scheduler calls `tick()` on startup (`monitor_scheduler_loop` in `backend/app/services/job_runner.py`), and `claim_due_monitors` takes every row with `status = 'active'` and `next_run_at <= now()`. The cutover rehearsal ran 2 of the 3 immediately. Each run is about 30 Metapi records, which is more than the remaining free quota if all 3 fire. Pause them with `docs/w8/pause-monitors.sql` (step 7) **before** the deploy that sets `EMBEDDED_WORKER_ENABLED=true`. Do not "accept the cost."
6. Decide on `docs/w8/admin-cleanup.sql`. It is reviewed and not run. It demotes every admin except `cultleaderzoz.dev@gmail.com`, clears every other platform-admin flag, and suspends test domains. No `DELETE`. The file ends in `ROLLBACK`. Ziad approved the original six domains; the rehearsal suspended 191 of 231 accounts on those six. The five domains added after that rehearsal (`helix.io`, `helix.ai`, `helix.com`, `vynex.com`, `vhynex.com`) are not in the 191 count.
7. Generate locally, and keep only in a password manager:
   - the `helix_api_login` password;
   - `CREDENTIAL_ENCRYPTION_KEY`, different from `SECRET_KEY`.
8. Render dashboard → service **`helix-intelligence-ai`** (`srv-da3ocem7bikc73bfi4fg`) → Settings:
   - **Auto-Deploy: Off** (same as step 3)
   - **Health Check Path: `/api/health`**
   Do not look for a Render service named `helix-backend`. That was the blueprint name. The JSON field `service` in `/health` is still the string `helix-backend`; that is an API label, not the dashboard name. The live service is not Blueprint-managed; do not sync the blueprint to deploy.
9. **Neon branch slot.** Before the day if you can, otherwise at step 2 of the cutover: read the free-plan branch limit and the current branch count. The backup needs one free slot. Proposed leftover deletes are listed there. Nothing in this change deletes a branch.
10. **Vercel.** Merging to `main` likely auto-deploys the frontend. Hold production until the backend is healthy. The dashboard controls are **unverified from this repo** (step 8 and section 3a).

## 3. Cutover (about 30 minutes, low-traffic time)

The ordered copy for the day is `docs/w8/cutover-today.md`. This section is the evidence behind it.

1. **Freeze.** No admin changes. Note T0 (UTC).
2. **Proposed Neon leftover cleanup, then confirm a free branch slot.** Not executed by this change. Do it only with the owner's OK, and only before creating the cutover backup.
   - In the Neon console for project `quiet-dawn-26282927`, read the **free-plan branch limit** and the current branch count. This repo does not record the number. Creating `pre-w8-…` needs one free slot; at the limit, the backup fails and the cutover stops.
   - Never delete the live branch `dev` (`br-gentle-star-axcrbk22`). The empty leftover named `production` (`br-soft-mode-ax44ab32`) is also **not** on this list.
   - Proposed deletes, after confirming each branch still exists and is not the live database:

     ```bash
     # PROPOSED ONLY. Do not run from a docs change. Never target dev.
     neon branches delete prod-backup-pre-w8 --project-id quiet-dawn-26282927
     neon branches delete w8-final-rehearsal --project-id quiet-dawn-26282927
     neon branches delete w8-rehearsal-from-dev --project-id quiet-dawn-26282927
     neon branches delete test-remediation-fresh --project-id quiet-dawn-26282927
     ```

   - Re-read the branch list. `dev` / `br-gentle-star-axcrbk22` must still be there.
3. **Backup branch** of the live branch at T0 (instant, copy-on-write):
   `neon branches create --project-id quiet-dawn-26282927 --parent br-gentle-star-axcrbk22 --name pre-w8-<YYYYMMDD-HHMM>`
   Also note the plan's point-in-time restore window as a second safety net.
4. **Migrate from your machine, not Render.** Use the **current** owner URL on the **direct** host (no `-pooler`), copied from the Neon console, held only in your shell. Do **not** reset the owner password here. The old API is still serving with that URL. Rotating it now takes the live API down.

   ```bash
   cd backend
   export TEST_DATABASE_URL='<owner direct URL, never saved>'
   export HELIX_PLATFORM_ADMIN_EMAILS='cultleaderzoz.dev@gmail.com'
   python -m alembic upgrade head
   python -m alembic check      # must print: No new upgrade operations detected.
   ```

   The old API keeps serving throughout. Its writes land in the migrated schema (section 1).
5. **Login role, created by SQL as the owner** (not `neon roles create`, which adds the role to `neon_superuser`):

   ```sql
   CREATE ROLE helix_api_login LOGIN PASSWORD '<generated>' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS INHERIT;
   GRANT helix_app TO helix_api_login;
   GRANT helix_worker TO helix_api_login;   -- embedded worker (free plan)
   ```

   Check: `select rolbypassrls from pg_roles where rolname='helix_api_login'` must be false.
6. **Admin cleanup** (`docs/w8/admin-cleanup.sql`), only if approved. Review the previews, then `COMMIT`. The file defaults to `ROLLBACK`. It must leave exactly one `role = 'admin'` and one `is_platform_admin`, both `cultleaderzoz.dev@gmail.com`. It must not suspend that account or any `@gmail.com` account.
7. **Pause all 3 overdue monitors before the embedded worker can start.** Run `docs/w8/pause-monitors.sql` as the owner, against `dev`, after the backup. The preview must be exactly 3 active daily rows with `next_run_at` in the past. `COMMIT` only then, and re-read: zero rows with `status = 'active' AND next_run_at <= now()`. Do not start step 10 until that re-read is done. The in-app Pause control on `/monitors` updates only the signed-in workspace (`update_monitor` is scoped by `org_id`), so it is not enough unless you have already confirmed all 3 monitors belong to that one workspace and you pause each of them. There is no Shell on this free service.
8. **Merge PR 31 into `main` only after its base is `main` and Render Auto-Deploy is off.** Render then builds nothing. **Vercel likely builds and may move the production domain** (section 3a). Hold or roll back the frontend until step 13. Do not promote it in this step.
9. **Check the env locally, then delete the file.** The Render export is plaintext secrets (`DATABASE_URL`, `SECRET_KEY`, provider keys). Compose the intended values in a local file, or download an export only onto that machine. From `backend/`:

   ```bash
   python scripts/check_release_env.py --env-file "<local file>"
   ```

   Every line must be `OK`. Then delete the file and empty the trash. Do not commit it, paste it, or leave it in Downloads. If you export again after the deploy to confirm what Render stored, delete that copy too.
10. **Deploy-moment: one button, `Save, rebuild and deploy`.** On `helix-intelligence-ai` → Environment, enter the values below and use **Save, rebuild, and deploy** (the dashboard label). Do not use **Save only**, and do not follow it with a separate Manual Deploy. A free instance that restarts between a save and a deploy boots `5b45806` with the new environment. With the health check set, Render switches traffic only when `/api/health` answers.

    **Deploy-moment group** (old code changes behavior if a restart sees these; they ride this button and are not saved earlier):

    - `DATABASE_URL`: `helix_api_login` on the **pooled** host of `br-gentle-star-axcrbk22`. `5b45806` does not set the RLS tenant settings, so this URL returns no rows (section 1). The new process refuses the owner role.
    - `SECRET_KEY`, when it is rotated in this cutover. The running process signs sessions with whatever key it loaded. A restart of `5b45806` on the new key signs everyone out before the new code is up.

    **Not in the deploy-moment group: `HELIX_DISPATCH_INLINE`.** Set it to `false` or leave it unset, on this same button for convenience. `main` at `5b45806` (`5b458061c04ee772a49b123568fd008c14e9d646`) provably ignores it, so it does not belong in the group:

    - `git grep -n HELIX_DISPATCH_INLINE 5b45806` returns no matches. The name does not occur in that tree.
    - `backend/app/services/work_outbox.py` is the W8 reader (`inline_execution_enabled()`). That file is not in `5b45806` (`git cat-file -e 5b45806:backend/app/services/work_outbox.py` fails). `backend/app/services/embedded_worker.py` is not in that commit either.
    - `Settings` at that commit uses `extra="ignore"` (`backend/app/core/config.py`), so an unknown variable is not bound onto settings.
    - W8 rejects `HELIX_DISPATCH_INLINE=true` when `ENVIRONMENT=production` (`backend/app/core/config.py`). That guard does not exist on `5b45806`.

    `EMBEDDED_WORKER_ENABLED` is also absent from `5b45806` (`git grep EMBEDDED_WORKER 5b45806` is empty), so the old process ignores it. It is still what starts the loop on the new process (`embedded_worker.start` during API lifespan). That is why step 7 is committed before this button, not because the old process would read the variable.

    `ENVIRONMENT=production` is read by `5b45806` in `storage_service.is_production()`. That function is already true when `ENVIRONMENT` is `production` or `prod`, **or** when `RENDER` is non-empty. Render's own docs say it sets `RENDER` on a service; this change did not re-read the live export to confirm the variable is present. If `RENDER` is set, adding `ENVIRONMENT` does not newly flip the function. If it is not, a Save-only of `ENVIRONMENT=production` makes the old process require R2 for media and raise when R2 is unset. Put `ENVIRONMENT` on this same button either way. Do not Save-only it. W8 will not boot in production without it.

    Also set on this button:

    - `ENVIRONMENT=production`
    - `PUBLIC_APP_BASE_URL` and `APP_BASE_URL` (the Vercel URL)
    - `BACKEND_CORS_ORIGINS`: Vercel origin(s) only
    - `CREDENTIAL_ENCRYPTION_KEY`
    - `RESEND_API_KEY` and `RESEND_FROM`
    - `EMBEDDED_WORKER_ENABLED=true`
    - `HELIX_DISPATCH_INLINE=false` (or unset; see the evidence above)
    - `METAPI_MONTHLY_RECORD_BUDGET` (the remaining records)
    - `DATABASE_URL` and `SECRET_KEY` as in the deploy-moment group

    Keep the **current** owner URL in the password manager until step 12. It is the rollback credential only until the owner password is reset.
11. **Verify the backend before anything else.** `/api/health` must be 200 on the new deploy. If it is not, roll back (section 4) and do not do steps 12–13.
12. **Rotate the Neon owner password only after that health check.** Neon console → Roles → `neondb_owner` → Reset password. Store the **new** owner URL (direct host for later migrations, and the URL a code rollback would paste into `DATABASE_URL`). The live process is on `helix_api_login`, so this reset does not restart it. The pre-rotation password is no longer the rollback credential. If step 11 failed, skip this step; the owner URL from T0 still works.
13. **Frontend.** Promote the Vercel deployment that matches this merge, only now (section 3a).
14. **Verify:**
    - `/api/health`
    - sign in as the admin
    - `/api/public/pricing`
    - one search (≤ 15 Metapi records) finishes through the embedded worker
    - admin Organizations and Pricing pages
    - the three monitors are still paused (they must not have run)
15. **Unfreeze.** Confirm the env file from step 9 is already deleted.

### 3a. Vercel production hold (dashboard steps unverified from this repo)

Merging `fix/core-W8` into `main` likely auto-deploys the frontend. Hold that production deployment until step 11 is healthy.

What the repo shows:

- `README.md` says `main` deploys to Render and Vercel.
- `DEVELOPMENT.md` says Render deploys `main` only, auto-deploy on commit, PR previews off. It does not document a Vercel auto-deploy toggle.
- `vercel.json` sets the framework, build, headers and the SPA rewrite. It has no `git.deploymentEnabled` and no production-branch setting.

The project's actual Vercel Git settings were not opened. Treat the controls below as **unverified**:

1. **Before the merge,** if the project has it: Vercel → Project → Settings → Environments → Production, and turn off automatic promotion onto the production domains ("Auto-assign Custom Production Domains", or the equivalent promote-automatically control). A merge can then build without moving the production domain. If that control is not there, use step 2.
2. **If the production domain already moved:** Vercel → Deployments → the previous production deployment → **Instant Rollback** (or Promote that previous deployment). That puts the last good frontend back on the production domain. The new deployment stays in the list.
3. **After step 11 is healthy:** Promote the deployment built from the merge commit.
4. **If the backend is rolled back:** Instant Rollback the frontend to that same previous deployment, then roll the API back (section 4).

## 4. Rollback

**Code problem before step 12** (new deploy unhealthy; owner password not rotated):
1. On `helix-intelligence-ai`, put `DATABASE_URL` back to the **owner URL that was live at T0**. Clear `EMBEDDED_WORKER_ENABLED` (the old code ignores it, but the next new boot must not start the loop). Do this and the rollback in the same window. The new code refuses the owner role (`assert_rls_role`); the old code fail-closes on `helix_api_login`. Neither mixed state should be left running.
2. Render → Rollback to the previous deploy (`5b45806`). Free plans keep only the last 2 deploys, so don't deploy anything else in between.
3. Vercel → Instant Rollback (section 3a). Unverified as a dashboard label; it is the documented Vercel control for returning the previous production deployment.
4. **Keep the migrated database.** The old code runs on it, so every write since T0 stays.

**Code problem after step 12** (owner password already reset): same steps, but `DATABASE_URL` is the **new** owner URL from the password manager. The pre-rotation password no longer works.

**Migration fails at step 4:** each migration is transactional. The database stays at the last good revision and the old code keeps working. Fix forward, or restore. The owner password has not been rotated yet.

**Data corruption (last resort):**
1. Put the app in maintenance (`DISCOVER_ENABLED=false`, freeze admin).
2. Export rows created after T0 from `users`, `organizations`, `scrape_jobs`, `support_tickets` and `saved_creatives` (`created_at > T0`).
3. Restore the live branch from `pre-w8-…` (Neon "Restore" to the backup branch, or to a timestamp).
4. Re-insert the exported rows.
5. Restore the owner `DATABASE_URL` (the new one if step 12 already happened, otherwise the T0 one) and roll back the code.

Down-migrations are **not** a rollback path: some W8 migrations quarantine or backfill data.

## 5. Free worker limits

See `docs/w8/free-worker.md`. In short:
- The service sleeps after about 15 minutes idle, and queued work waits for the next request.
- Scheduled monitors run only while it's awake; missed runs are not backfilled.
- A wake-up ping makes runs likely, not guaranteed.
- A job interrupted by spin-down is rerun after 120 s.

## 6. Rehearsal record

End-to-end run on `w8-cutover-rehearsal` (`br-bitter-boat-axjl0hax`, a fresh copy of `dev`),
2026-11-10. The migrate, the login role, and a local stand-in for the new API were run with the same commands and roles as above. Step numbers below are the rehearsal record, not the current cutover numbering:

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

