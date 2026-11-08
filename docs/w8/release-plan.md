# W8 release plan: compatibility, cutover and rollback (2026-11-08)

> **Update 2026-11-08 (later): the live database is the Neon branch `dev`, not `production`.**
> Render's environment export points `DATABASE_URL` at `ep-cold-rice-axydlqmv` (branch `dev`,
> `br-gentle-star-axcrbk22`), revision `b1c2d3e4f5a6`, 230 users / 197 workspaces. Read every
> "production" below as that branch. Rehearsed on a fresh copy of `dev` (`w8-dev-rehearsal-2`):
> all migrations through `c9e1f3a5b7d0` applied, row counts unchanged except 2 workspace-less
> patterns moved to `pattern_quarantine`, `alembic check` clean. The old backend (`main`) ran
> against that migrated copy as the owner: health, sign-up/in, session, reads, and creating a
> search, ticket and monitor all 200. The reconciliation migration is a no-op on the clean
> `production` branch copy. Roles `helix_api_login` / `helix_worker_login` must be confirmed on
> `dev` before cutover.

Release candidate: `fix/core-W8` at `ea71a51` (CI green, all 8 jobs; docs-only commits may follow). Production Neon branch: `production` (`br-soft-mode-ax44ab32`), revision `c4d92e1f7a8b`, 1 user, 1 workspace, 2 plans. Nothing below has been run on production.

## 1. Evidence

| Check | Result |
|---|---|
| All 25 migrations on a fresh copy of production (`w8-final-rehearsal`) | Applied, no errors; row counts unchanged (1 / 1 / 2); `alembic check` clean |
| Old backend (`main` @ `5b45806`) against that migrated copy, as the owner role | Starts; health, sign-up, sign-in, session, profile, jobs, saved, monitors, notifications, updates and support reads, plus creating a search and a support ticket, all 200 |
| Old backend's search pipeline | Fails on provider outage with `refund() got an unexpected keyword argument 'org'`. This is a bug **already in `main`**, independent of the schema |
| New backend with restricted logins | Exercised all day on `w8-rehearsal` (restricted API and worker logins, RLS on) |

**Conclusion.** The schema change is forward-compatible with the running code, so the database can be migrated **before** the code changes, while the old API keeps serving.

## 2. Why old code still works

- The production owner role has `BYPASSRLS`, so the new row-level-security policies do not apply to the old code's connection.
- No column the old code reads or writes is dropped or renamed. W8 adds tables and columns, and tightens defaults that old inserts already satisfy (verified by the inserts above).
- The new code **will not** start with the owner role in production (`assert_rls_role`). It must use `helix_api_login`, which exists in production and does not bypass RLS. Its password must be set and put in Render before the deploy.

## 3. Cutover order (writes stay safe at every step)

1. **Freeze**. Pause manual admin changes. Note the time T0.
2. **Backup branch** from production at T0 (`prod-backup-pre-w8` exists from earlier today; make a fresh one at T0).
3. **Migrate production** as the owner (`alembic upgrade head`, then `alembic check`). The old API keeps serving; its writes land in the migrated schema (proven above).
4. **Roles**:
   - `GRANT helix_app TO helix_api_login;`
   - `GRANT helix_worker TO helix_worker_login;`
   - Embedded worker only: `GRANT helix_worker TO helix_api_login;`
   - Set the login passwords if not already known.
5. **Render settings** (API service): see section 5. Add them before merging. The old code ignores the new ones.
6. **Merge `fix/core-W8` into `main`.** Render builds the new API, and the pre-deploy runs `alembic upgrade head` (a no-op) and `alembic check`. Render switches traffic only after the new instance is healthy. Requests in flight on the old instance finish. A search that the old code was running inline is lost with that instance; reconciliation marks it failed at its deadline. Vercel builds the new frontend.
7. **Verify**: health, sign-in, `/api/public/pricing`, one search (≤ 15 records), admin pages.
8. **Admin**: sign up `cultleaderzoz.dev@gmail.com` on production, then run `scripts/bootstrap_platform_admin.py --expect-branch br-soft-mode-ax44ab32`.

## 4. Rollback (keeps every write made after cutover)

- **Code problem** (most likely): redeploy the previous Render deploy (`5b45806`) and the previous Vercel deployment. **Keep the migrated database.** The old code runs on it (section 1), so every row written by the new code since T0 stays.
  - Rows only the new code uses (trial grants, pricing, archive, drafts, plan limits) are ignored by the old code but remain for the next attempt.
  - The new embedded worker stops with it, so queued searches wait.
- **Migration problem during step 3** (fails partway): Alembic runs each migration in a transaction, so a failed step rolls back. The database stays at the last good revision, and the old code keeps working. Fix forward, or restore.
- **Restore from the backup branch** is the last resort, for corruption only. It **loses writes after T0**. Before restoring:
  - export the rows created after T0 from `users`, `organizations`, `scrape_jobs`, `support_tickets` and `saved_creatives` (by `created_at > T0`), and re-insert them afterwards;
  - put the app in read-only mode first, so no further writes happen.
- **Down-migrations are not a rollback path.** Several W8 migrations backfill or quarantine data and are not reversible without loss.

## 5. Production configuration to verify on Render (values not shared)

Must exist on the API service for the new code to start or deploy:

- `ENVIRONMENT=production`
- `PUBLIC_APP_BASE_URL` and `APP_BASE_URL` as public `https://` origins
- `BACKEND_CORS_ORIGINS`: the Vercel origin(s) only, no `localhost`
- `SECRET_KEY` (≥ 32 chars)
- `CREDENTIAL_ENCRYPTION_KEY`, different from `SECRET_KEY`
- `RESEND_API_KEY` and `RESEND_FROM`
- `GROQ_MODEL` and `GEMINI_TEXT_MODEL` (code defaults exist)
- `HELIX_DISPATCH_INLINE=false`
- `DATABASE_URL`: `helix_api_login` on the **production** endpoint (`ep-fancy-bread`), not the owner and not `ep-cold-rice` (the `dev` branch)
- `MIGRATION_DATABASE_URL`: the owner on the production endpoint
- `HELIX_RELEASE_MIGRATIONS_APPROVED=yes`, at release time only
- `EMBEDDED_WORKER_ENABLED=true`, if using the free worker
- `METAPI_API_KEY`, rotated
- `METAPI_MONTHLY_RECORD_BUDGET`: the remaining records
- `DISCOVER_*` caps as decided

Safe verification without exposing values: a one-off Render shell, or a temporary pre-deploy step, running `python -c "from app.core.config import settings"` with `ENVIRONMENT=production`. That command runs the same validator as startup and prints only the failing **names**. This is stronger than checking names, because it validates the values too. The env file supplied today points `DATABASE_URL` at the `dev` branch with the owner role and lacks most of the above, so it is not the production configuration.

## 6. Re-rehearsal after worker changes

The embedded worker added no migration (head is still `b8d0f2a4c6e9`), so the migration rehearsal stands. The code-level change needs CI on the exact release commit. The role grant in step 4 should be rehearsed once on a fresh production copy together with a restricted-login search, as was done on `w8-rehearsal`.
