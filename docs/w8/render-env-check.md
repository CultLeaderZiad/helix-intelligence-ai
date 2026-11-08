# Render production config check for W8 (prints no values)

Paste into **Render → helix-backend → Shell**. It reads the service's environment
and checks the rules W8 enforces at startup in production, and checks the
database login. Output is names, true/false and role names only.

```bash
python3 - <<'PY'
import os, asyncio
from urllib.parse import urlsplit
E = os.environ.get
ok = lambda b: "OK  " if b else "FAIL"
def https_public(v):
    try: p = urlsplit(v or "")
    except ValueError: return False
    return p.scheme == "https" and bool(p.hostname) and p.hostname not in ("localhost", "127.0.0.1", "::1")
rows = []
rows.append(("ENVIRONMENT is production", E("ENVIRONMENT", "").strip().lower() == "production"))
for n in ("PUBLIC_APP_BASE_URL", "APP_BASE_URL"):
    rows.append((f"{n} is a public https origin", https_public(E(n))))
cors = [o.strip() for o in (E("BACKEND_CORS_ORIGINS") or "").split(",") if o.strip()]
rows.append(("BACKEND_CORS_ORIGINS set", bool(cors)))
rows.append(("BACKEND_CORS_ORIGINS all public https (no localhost)", bool(cors) and all(https_public(o) for o in cors)))
sk, ck = E("SECRET_KEY") or "", E("CREDENTIAL_ENCRYPTION_KEY") or ""
rows.append(("SECRET_KEY >= 32 chars", len(sk) >= 32))
rows.append(("CREDENTIAL_ENCRYPTION_KEY set and differs from SECRET_KEY", bool(ck) and ck != sk))
rows.append(("RESEND_API_KEY and RESEND_FROM set", bool(E("RESEND_API_KEY")) and bool(E("RESEND_FROM"))))
rows.append(("HELIX_DISPATCH_INLINE is false/unset", (E("HELIX_DISPATCH_INLINE") or "false").lower() not in ("true", "1", "yes")))
rows.append(("AUTH_DEV_RESET_RETURN is false/unset", (E("AUTH_DEV_RESET_RETURN") or "false").lower() not in ("true", "1", "yes")))
apify_on = (E("APIFY_ENABLED") or "").lower() == "true"
rows.append(("Apify off, or on with APIFY_API_TOKEN", (not apify_on) or bool(E("APIFY_API_TOKEN"))))
rows.append(("METAPI_API_KEY set", bool(E("METAPI_API_KEY") or E("METAPI_KEY") or E("METAPI_TOKEN"))))
rows.append(("MIGRATION_DATABASE_URL set", bool(E("MIGRATION_DATABASE_URL"))))
for name, good in rows:
    print(ok(good), name)
print("info EMBEDDED_WORKER_ENABLED =", (E("EMBEDDED_WORKER_ENABLED") or "false").lower())
print("info HELIX_RELEASE_MIGRATIONS_APPROVED =", "yes" if E("HELIX_RELEASE_MIGRATIONS_APPROVED") == "yes" else "not yes")
def endpoint(u):
    h = (urlsplit(u).hostname or "")
    return h.split(".")[0].replace("-pooler", "")
async def db(label, url, want_owner):
    try:
        import asyncpg
        dsn = url.replace("postgresql+asyncpg://", "postgresql://")
        c = await asyncpg.connect(dsn, timeout=20)
        r = await c.fetchrow("select current_user u, rolbypassrls b from pg_roles where rolname = current_user")
        app_m = await c.fetchval("select exists(select 1 from pg_roles where rolname='helix_app') and pg_has_role(current_user,'helix_app','MEMBER')")
        wrk_m = await c.fetchval("select exists(select 1 from pg_roles where rolname='helix_worker') and pg_has_role(current_user,'helix_worker','MEMBER')")
        rev = await c.fetchval("select version_num from alembic_version")
        await c.close()
        prod = endpoint(url) == "ep-fancy-bread-axe99xvb"
        print(ok(prod), f"{label} points at the production branch endpoint ({endpoint(url)})")
        if want_owner:
            print("info", f"{label} role = {r['u']}, bypassrls = {r['b']}")
        else:
            print(ok(not r["b"]), f"{label} role = {r['u']} does not bypass RLS")
            print(ok(app_m), f"{label} role is a member of helix_app")
            print("info", f"{label} member of helix_worker (needed for embedded worker) = {wrk_m}")
        print("info", f"{label} alembic revision = {rev}")
    except Exception as exc:
        print("FAIL", f"{label} could not be checked: {type(exc).__name__}")
async def main():
    if E("DATABASE_URL"): await db("DATABASE_URL", E("DATABASE_URL"), False)
    else: print("FAIL DATABASE_URL not set")
    if E("MIGRATION_DATABASE_URL"): await db("MIGRATION_DATABASE_URL", E("MIGRATION_DATABASE_URL"), True)
asyncio.run(main())
PY
```

Expected now (before any change): several `FAIL` lines. That is the to-do list.
Paste the output back; it contains no secrets.

Notes:
- `DATABASE_URL` must be `helix_api_login` on `ep-fancy-bread-axe99xvb`.
  `helix_app` membership comes from `GRANT helix_app TO helix_api_login;`.
  That grant is release step 4, so `FAIL` there is expected until then.
- Before the release, `alembic revision` should read `c4d92e1f7a8b`.
