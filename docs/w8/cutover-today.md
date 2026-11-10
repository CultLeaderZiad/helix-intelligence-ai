# W8 cutover today

Not started. Nothing here has been run. Ziad's approval starts at step 1 and continues through step 14. Stop at the first success signal that fails.

Free Render service **`helix-intelligence-ai`** (`srv-da3ocem7bikc73bfi4fg`, Ohio). No Shell, no pre-deploy command. Do not sync `render.yaml`. Database is Neon branch **`dev`** (`br-gentle-star-axcrbk22`, endpoint `ep-cold-rice-axydlqmv`). The branch named `production` is not this database. Never `neon roles create`.

Evidence: `release-plan.md`. Exact SQL: `pause-monitors.sql`, `admin-cleanup.sql`. Env names: `secret-rotation.md`, `render-env-check.md`.

The production merge is draft PR **#31** after its base is `main`. It currently targets `fix/intelligence-W7`. This file does not retarget or merge it. PR #32 is docs only.

## 1. Render Auto-Deploy off

- **Who:** Ziad, Render dashboard.
- **Do:** `helix-intelligence-ai` → Settings. Auto-Deploy **Off**. Health Check Path **`/api/health`**.
- **Success:** the page shows Auto-Deploy off and the health path saved. The running deploy is still `5b45806`.
- **Rollback:** leave it off until this cutover is finished or abandoned. Turning it on mid-cutover deploys `main` by itself.

## 2. Hold Vercel

- **Who:** Ziad, Vercel dashboard.
- **Do:** before the merge in step 10, stop the production domain from moving with that merge. If the project has it: Settings → Environments → Production → turn off automatic assignment of the production domains. If that control is missing and the domain moves at step 10: Deployments → the previous production deployment → **Instant Rollback** (or Promote that older deployment).
- **Success:** `https://helix-intelligence-ai-six.vercel.app` (the origin in `DEVELOPMENT.md`) still serves the previous frontend after step 10.
- **Rollback:** Instant Rollback to that same previous deployment.
- **Unverified:** `vercel.json` has no Git settings. The dashboard control and whether that host is still the production domain were not opened.

## 3. Backup `dev`

- **Who:** trusted machine. Ziad only if he is the one at that keyboard.
- **Do:** In the Neon console for project `quiet-dawn-26282927`, read the free-plan branch limit and the current count. The backup needs one free slot. If the project is at the limit, the only proposed deletes are `prod-backup-pre-w8`, `w8-final-rehearsal`, `w8-rehearsal-from-dev`, and `test-remediation-fresh`. Never delete `dev` (`br-gentle-star-axcrbk22`) or the branch named `production`. Then:

  ```bash
  neon branches create --project-id quiet-dawn-26282927 --parent br-gentle-star-axcrbk22 --name pre-w8-<YYYYMMDD-HHMM>
  ```

  Note T0 (UTC) and the plan's point-in-time window.
- **Success:** the new branch's parent is `br-gentle-star-axcrbk22`, and `dev` is still present.
- **Rollback:** this branch is the rollback copy. Do not delete it.
- **Unverified:** the numeric branch limit, and whether those four leftover branches still exist. The deletes are proposed, not run.

## 4. Retarget PR #31, do not merge yet

- **Who:** Ziad, GitHub.
- **Do:** PR #31 → Edit → base **`main`**. Read the diff against `main`. Do not click merge.
- **Success:** base ref is `main`. Render is still on `5b45806` because Auto-Deploy is off.
- **Rollback:** set the base back to `fix/intelligence-W7`.

## 5. Migrate `dev`

- **Who:** trusted machine, as the **current** owner, direct host (no `-pooler`). The URL stays in that shell. Do not reset the owner password. Do not write the URL to a file or into chat.
- **Do:**

  ```bash
  cd backend
  export TEST_DATABASE_URL='<owner direct URL>'
  export HELIX_PLATFORM_ADMIN_EMAILS='cultleaderzoz.dev@gmail.com'
  python -m alembic upgrade head
  python -m alembic check
  ```

- **Success:** upgrade exit 0, revision `c9e1f3a5b7d0`. `alembic check` prints `No new upgrade operations detected.` The old API keeps serving.
- **Rollback:** a failed migration stays at the last good revision. Stop. Do not rotate the owner password. Old code keeps the T0 owner URL.

## 6. Login roles, by SQL

- **Who:** trusted machine, same owner session. Not the Neon "create role" button and not `neon roles create` (that adds `neon_superuser`).
- **Do:** generate two passwords into the password manager only (`python -c "import secrets; print(secrets.token_urlsafe(32))"`). Then:

  ```sql
  CREATE ROLE helix_api_login LOGIN PASSWORD '<generated>' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS INHERIT;
  CREATE ROLE helix_worker_login LOGIN PASSWORD '<generated>' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS INHERIT;
  GRANT helix_app TO helix_api_login;
  GRANT helix_worker TO helix_api_login;     -- free plan: the API process is the worker
  GRANT helix_worker TO helix_worker_login;  -- not the Render DATABASE_URL
  ```

  ```sql
  SELECT rolname, rolsuper, rolbypassrls, rolcanlogin
  FROM pg_roles
  WHERE rolname IN ('helix_api_login', 'helix_worker_login', 'helix_app', 'helix_worker');

  SELECT r.rolname,
         pg_has_role(r.rolname, 'helix_app', 'MEMBER') AS app,
         pg_has_role(r.rolname, 'helix_worker', 'MEMBER') AS worker,
         pg_has_role(r.rolname, 'neon_superuser', 'MEMBER') AS neon_super
  FROM pg_roles r
  WHERE r.rolname IN ('helix_api_login', 'helix_worker_login');
  ```

- **Success:** both logins are `LOGIN`, `rolsuper` false, `rolbypassrls` false, `neon_super` false. `helix_api_login` is a member of `helix_app` and `helix_worker`. `helix_worker_login` is a member of `helix_worker` only. `helix_app` and `helix_worker` stay `NOLOGIN` (migration `e7c1a9b4d2f0` creates those two). Render's `DATABASE_URL` will be `helix_api_login` on the **pooled** host. Do not point the free service at `helix_worker_login`.
- **Rollback:** before step 11, `DROP ROLE` of a login that nothing has used yet. After step 11, do not drop roles; roll the app back with the owner URL (step 11).
- **Unverified:** the 2026-11-10 rehearsal created `helix_api_login` only. `helix_worker_login` was not in that run. `DEVELOPMENT.md` says the API login must not inherit `helix_worker`; that sentence is for a separate worker process. This free service has no second process, and the embedded loop will not claim jobs without the grant. Claim policies also require `helix.worker_claim`, which only the loop sets.

## 7. Pause the 3 monitors

- **Who:** trusted machine, owner, against `dev`, after step 3. Before any deploy with `EMBEDDED_WORKER_ENABLED=true`.
- **Do:** the file ends in `ROLLBACK`. First run, in a new `psql` session:

  ```bash
  psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f docs/w8/pause-monitors.sql
  ```

  The preview must be exactly 3 rows, each `cadence = daily`, each `next_run_at` in the past. If it is, comment `ROLLBACK`, uncomment `COMMIT`, and run the file again in a **new** session. Then re-read:

  ```sql
  SELECT id, name, cadence, status, next_run_at
  FROM monitors
  WHERE status = 'active' AND next_run_at IS NOT NULL AND next_run_at <= now();
  ```

- **Success:** that re-read returns zero rows. `paused_for_cutover` was 3. The in-app Pause button only updates the signed-in workspace, so it does not replace this SQL.
- **Rollback:** before step 11, set those three back to `active` only if you accept that they are due immediately. After the worker is live, leave them paused. Resuming without moving `next_run_at` forward runs them at the next tick (about 30 Metapi records each).

## 8. Admin cleanup

- **Who:** trusted machine, owner, same backup. Ziad has approved the original six suspend domains. The file also lists `helix.io`, `helix.ai`, `helix.com`, `vynex.com`, `vhynex.com`.
- **Do:** same two-pass as step 7, with `docs/w8/admin-cleanup.sql`. `COMMIT` only when the preview shows `missing_allowlisted` empty, no `gmail.com` domain in the suspend preview, and the apply block does not raise. The apply must show exactly one `role = admin` and one `is_platform_admin`, both `cultleaderzoz.dev@gmail.com`, `is_suspended` false, and `gmail_newly_suspended = 0`.
- **Success:** those counts, and the transaction committed. No `DELETE`.
- **Rollback:** restore `dev` from the step 3 branch, or re-promote specific user ids. There is no down-migration for this.
- **Unverified:** the five extra domains were not in the rehearsal that suspended 191 of 231 accounts.

## 9. Check env, delete the file

- **Who:** trusted machine, then Ziad does not keep a copy.
- **Do:** compose the values in step 11 in a local file. From `backend/`:

  ```bash
  python scripts/check_release_env.py --env-file "<local file>"
  ```

  The file is plaintext secrets. Every line must be `OK`. Delete it and empty the trash. Do not commit it or paste it.
- **Success:** exit 0, every line `OK`, file gone.
- **Rollback:** nothing is live yet. Delete the file even when the check fails.

## 10. Merge PR #31

- **Who:** Ziad, GitHub. Only after steps 1, 2, and 4.
- **Do:** merge PR #31 into `main`. Do not press Deploy on Render.
- **Success:** `main` contains the release commit. Render's live deploy is still `5b45806`. If Vercel moved the production domain, do step 2's Instant Rollback before step 11.
- **Rollback:** do not revert `main` as the app rollback. Roll Render and Vercel back in steps 11 and 14. With Auto-Deploy off, the merge alone does not change the API.

## 11. One deploy

- **Who:** Ziad, Render dashboard, service `helix-intelligence-ai`.
- **Do:** Environment → set the values below → **Save, rebuild, and deploy**. Not **Save only**, and not a later Manual Deploy. A free-instance restart between those boots `5b45806` with the new `DATABASE_URL` and fail-closes.

  Deploy-moment (do not save these earlier): `DATABASE_URL` = `helix_api_login` on the pooled host of `br-gentle-star-axcrbk22` (`ep-cold-rice-axydlqmv`); `SECRET_KEY` if it is rotated now (≥ 48 random chars, password manager).

  Same button, not deploy-moment: `ENVIRONMENT=production`, `PUBLIC_APP_BASE_URL` and `APP_BASE_URL` (the Vercel origin), `BACKEND_CORS_ORIGINS` (that https origin only, no `localhost`), `CREDENTIAL_ENCRYPTION_KEY` (different from `SECRET_KEY`), `RESEND_API_KEY`, `RESEND_FROM`, `EMBEDDED_WORKER_ENABLED=true`, `HELIX_DISPATCH_INLINE=false`, `METAPI_MONTHLY_RECORD_BUDGET` (remaining records on the Metapi dashboard today).

  `HELIX_DISPATCH_INLINE` is outside the deploy-moment group because `main` at `5b45806` has no such name (`git grep` empty, `work_outbox.py` absent, `Settings.extra=ignore`). W8 still refuses to boot if it is true. `EMBEDDED_WORKER_ENABLED` is also absent from `5b45806`; it starts the loop only on the new process, which is why step 7 is already committed.
- **Success:** the new deploy is Live and `GET /api/health` returns 200 with `"db":"connected"`. The JSON `"service"` value `helix-backend` is the API label, not the Render name. Render waits for `/api/health` only if step 1 saved the health path.
- **Rollback:** in one window, set `DATABASE_URL` back to the **T0 owner URL** (the password is not rotated yet), clear `EMBEDDED_WORKER_ENABLED`, and Rollback to `5b45806`. Free plans keep only the last 2 deploys. The new code refuses the owner role; the old code fail-closes on `helix_api_login`. Keep the migrated database.
- **Unverified:** whether the live service has `RENDER` set. Do not Save-only `ENVIRONMENT=production` either.

## 12. Health, then stop if it fails

- **Who:** trusted machine. Passwords and tokens stay out of chat.
- **Do:**

  ```bash
  curl -si https://helix-intelligence-ai.onrender.com/api/health
  ```

  Owner, expect HTTP 200, `"role":"admin"`, and an `access_token`:

  ```bash
  curl -si -X POST https://helix-intelligence-ai.onrender.com/api/auth/sign-in \
    -H 'content-type: application/json' \
    -d '{"email":"cultleaderzoz.dev@gmail.com","password":"<password>"}'
  ```

  With that token, both must be HTTP 200:

  ```bash
  curl -si https://helix-intelligence-ai.onrender.com/api/admin/organizations \
    -H "authorization: Bearer <token>"
  curl -si https://helix-intelligence-ai.onrender.com/api/admin/plans \
    -H "authorization: Bearer <token>"
  ```

  Pick one demoted account that is **not** on the suspend list (a suspended account fails sign-in, which does not test the admin gate). Sign in, then the same two GETs must be HTTP 403.
- **Success:** health 200 with `"db":"connected"`; owner 200 on both admin routes; that ex-admin 403 on both. Re-read the monitor query in step 7 and still get zero due rows.
- **Rollback:** step 11's rollback. Do not do steps 13 or 14.
- **Unverified:** which ex-admin account is still able to sign in. The rehearsal's 403s were on a copy, not on this deploy.

## 13. Rotate the owner password

- **Who:** Ziad, Neon console. Only after step 12 succeeded.
- **Do:** Roles → `neondb_owner` → Reset password. Store the **new** owner URL (direct host for later migrations, and the URL a code rollback would paste into `DATABASE_URL`). The live process is on `helix_api_login`, so this does not restart it.
- **Success:** the new URL is in the password manager. The pre-rotation password is no longer the rollback credential.
- **Rollback:** there is no un-rotate. Later code rollback uses this new URL. If step 12 failed, skip this step; the T0 owner URL still works.

## 14. Release Vercel

- **Who:** Ziad, Vercel. Only after step 12 succeeded.
- **Do:** Promote the deployment built from the merge commit onto the production domain.
- **Success:** the production origin loads, and its API calls go to `https://helix-intelligence-ai.onrender.com`.
- **Rollback:** Instant Rollback to the previous production deployment, then step 11's API rollback if the API is also bad.
- **Unverified:** the Promote control was not confirmed from the repo.

Then unfreeze. Confirm the env file from step 9 is already deleted. Leave the three monitors paused until `next_run_at` is moved forward on purpose.
