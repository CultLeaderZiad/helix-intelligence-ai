# W8 — Login latency and what production needs

Measured on 2026-11-05 against the Neon dev branch `dev-w8`
(`br-fragrant-sun-axi0mwwh`, endpoint `ep-withered-bar-axr1ow4u`, us-east-2),
not production. The API ran locally as `helix_api_login` with
`SERVER_TIMING_ENABLED=true`. Every number below came from the
`Server-Timing` header or the browser's Resource Timing API.

## Why login was slow

The test machine is far from us-east-2: one `SELECT 1` round trip took a
median of **149–151 ms** and a new TLS connection took **~1.0–1.1 s**. Because
of that distance, round-trip count shows up clearly in the totals.

| Request | Before W8 | After W8 |
|---|---|---|
| `POST /api/auth/sign-in` SQL statements | 28 | 10 |
| `GET /api/auth/session` SQL statements | 27 | 10 |
| RLS `set_config` statements per request | 16 | 3 |
| `pool_pre_ping` per checkout | ~600 ms (≈4 round trips) | ~150 ms (1) |
| Writes on a session read | 2 `UPDATE organizations` (rolled back) | 0 |
| Warm sign-in, server total | 5.3–5.7 s | 1.8–2.0 s |
| Warm session, server total | 5.1–5.7 s | 1.8–1.9 s |
| Password hash (PBKDF2, 100k) | 28–35 ms | 28–56 ms (unchanged) |

Code causes, all fixed on `fix/core-W8`:

1. The tenant `after_begin` listener was registered twice, once per session
   maker, because both makers share one `Session` class. Every transaction
   set its RLS context twice.
2. Each RLS application took four separate `set_config` statements.
3. Sign-in loaded the same user twice. Owned and member org ids took two
   queries, and plans were re-selected.
4. `GET /auth/session` flushed daily counter "resets" (`UPDATE
   organizations`) that were never committed. Each request did the write,
   took a row lock, and rolled it back.
5. SQLAlchemy's asyncpg `pool_pre_ping` wraps its probe in
   BEGIN/fetchrow/ROLLBACK.

Not a cause: password hashing (~30–55 ms here; see hosting note below).

## Browser, end to end (local Vite → local API → dev-w8)

| Step | Time |
|---|---|
| UI sign-up (`/api/auth/sign-up`) | 3.1 s, then `/discover` |
| UI sign-in (`/api/auth/sign-in`) | 2.0 s |
| Post-login calls (`/updates/banner`, `/notifications/`, `/updates`) | fired in parallel; slowest done at 4.8 s after click (it opened a new connection: 0.99 s) |
| Sign-out (`/api/auth/sign-out`) | 1.7 s, token cleared, `/sign-in` |

Verified in the browser: sign-up, sign-in, reload keeps the session,
sign-out revokes server-side, access request on `/access`, admin approval
on `/admin/access-requests`, and the user then sees `approved` with only
`discover` enabled.

## Hosting vs code

Code (fixed here): the round-trip count. Every authenticated request still
costs about 4 round trips before route work starts (RLS scope, user, org
ids, RLS scope). The total is still RTT × statements.

Hosting (not fixable in code; unverified, because the Render dashboard
was not inspected):

- `render.yaml` sets no `region`, so Render uses its default (Oregon).
  Neon is us-east-2 (Ohio). If that holds, each DB round trip in
  production costs tens of ms instead of ~1 ms, and a 10-statement sign-in
  pays it 10 times. **Moving the Render service to Ohio, the same region
  as Neon, is the biggest remaining lever.**
- Render free tier sleeps after 15 minutes. Locally the process alone took
  **7.9 s** from start to first `/health` 200. A Render wake adds container
  start on top of that.
- Neon autosuspend: after 6 min 43 s with no traffic to dev-w8, a fresh API
  process took **7.9 s** to its first `/health` 200 (startup connects to the
  DB for the RLS role check). That matches the warm-Neon start (7.9 s). The
  first sign-in then took **3.3 s** (10 statements, ~300 ms each vs ~180 ms
  warm). The second took **4.0 s** because it opened a second pool
  connection (~1.0 s). Whether Neon actually suspended is **unconfirmed**:
  the branch's autosuspend setting was not inspected, and no extra wake time
  showed up beyond noise.
- A sequential request right after another can open a new pool connection
  (~1 s at this distance), because the previous request's session is still
  closing. At production traffic the pool stays warm; on a cold single
  instance it is paid once or twice.
- PBKDF2 at 100k iterations costs ~30–55 ms on this machine's CPU. On
  Render free (0.1 CPU) expect it to be several times slower. Measure
  there with `SERVER_TIMING_ENABLED=true` before changing iterations.

## What production needs before this stack can ship

Do not run any of this until the owner approves.

### Database roles

On dev-w8 the login roles `helix_api_login` and `helix_worker_login`
already existed (copied from the parent branch), both `LOGIN`,
`NOSUPERUSER`, `NOBYPASSRLS`, `INHERIT`. Production most likely has them
too. Verify that before creating anything.

1. Back up or branch production first (a Neon branch is instant).
2. Run migrations as the owner, from `c4d92e1f7a8b` to `d1f9c4a7b263`
   (14 revisions). They took 4 min 43 s on dev-w8 and `alembic check`
   reported no drift. Render's `preDeployCommand` already gates this on
   `HELIX_RELEASE_MIGRATIONS_APPROVED=yes` and `MIGRATION_DATABASE_URL`.
   Use the **direct** (non `-pooler`) host for migrations.
3. Migration `e7c1a9b4d2f0` creates the `NOLOGIN` group roles `helix_app`
   and `helix_worker`. Then grant:

   ```sql
   GRANT helix_app TO helix_api_login;
   GRANT helix_worker TO helix_worker_login;
   ```

   On Neon, the owner cannot set `NOSUPERUSER`/`NOBYPASSRLS` through
   `ALTER ROLE` (it is not a superuser). Those attributes are already
   correct on the existing roles. Change only the password, from a secret
   store: `ALTER ROLE ... WITH PASSWORD ...`.
4. API login must not inherit `helix_worker` (maintenance policies are
   worker-only). Verified on dev-w8: `helix_api_login → helix_app` only.

### Environment (Render)

| Service | Variable | Value |
|---|---|---|
| API | `DATABASE_URL` | `helix_api_login` on the **pooler** host, `sslmode=require` |
| Worker | `DATABASE_URL` | `helix_worker_login` |
| API (release only) | `MIGRATION_DATABASE_URL` | owner role, direct host |
| both | `ENVIRONMENT` | `production` |
| both | `ALLOWED_REMOTE_DATABASE_HOST`, `PRODUCTION_DATABASE_HOST` | leave unset; ignored in production |

With the owner role in `DATABASE_URL`, W2+ refuses to boot in production.
That is intended.

### Worker

The Render Background Worker must use `backend/workers/jobs/Dockerfile`
(W8 replaced `backend/workers/scrapling/`, which is deleted). It runs Discover
and Monitor work items plus job reconciliation and needs no browser.

### Hosting

- Put the Render API and worker in the same region as Neon (us-east-2 /
  Ohio).
- Decide on Render free tier sleep (paid instance or keep-warm ping) after
  measuring a real cold start there with `SERVER_TIMING_ENABLED=true`.
