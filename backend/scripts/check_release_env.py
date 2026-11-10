"""Check a Render environment export against what W8 needs in production.

Render's free plan has no Shell. The service is helix-intelligence-ai
(srv-da3ocem7bikc73bfi4fg), not helix-backend. Export its Environment to a
local .env. That file is plaintext secrets: run this check, then delete the
file. Never commit it or paste it into chat. From backend/:

    python scripts/check_release_env.py --env-file "C:/path/to/render.env"

It prints only OK/FAIL, setting names, role names, Neon branch/endpoint ids and
the migration revision. Never values. Database checks are read-only.
"""
from __future__ import annotations

import argparse
import asyncio
import re
from urllib.parse import urlsplit

LIVE_BRANCH = "br-gentle-star-axcrbk22"   # the Neon branch named `dev` = production
LIVE_ENDPOINT = "ep-cold-rice-axydlqmv"
TRUE = ("true", "1", "yes")


def load_env(path: str) -> dict:
    text = open(path, encoding="utf-8").read().replace('\n"', '"')
    out = {}
    for line in text.splitlines():
        m = re.match(r"^\s*([A-Z0-9_]+)\s*=(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"').strip("'").strip()
    return out


def https_public(value: str) -> bool:
    try:
        p = urlsplit(value or "")
    except ValueError:
        return False
    return p.scheme == "https" and bool(p.hostname) and p.hostname not in ("localhost", "127.0.0.1", "::1")


def static_checks(env: dict) -> list[tuple[bool, str]]:
    g = env.get
    cors = [o.strip() for o in (g("BACKEND_CORS_ORIGINS") or "").split(",") if o.strip()]
    secret, cred = g("SECRET_KEY") or "", g("CREDENTIAL_ENCRYPTION_KEY") or ""
    rows = [
        ((g("ENVIRONMENT") or "").lower() == "production", "ENVIRONMENT is production"),
        (https_public(g("PUBLIC_APP_BASE_URL")), "PUBLIC_APP_BASE_URL is a public https origin"),
        (https_public(g("APP_BASE_URL")), "APP_BASE_URL is a public https origin"),
        (bool(cors), "BACKEND_CORS_ORIGINS set"),
        (bool(cors) and all(https_public(o) for o in cors), "BACKEND_CORS_ORIGINS all public https (no localhost)"),
        (len(secret) >= 32, "SECRET_KEY >= 32 chars"),
        (bool(cred) and cred != secret, "CREDENTIAL_ENCRYPTION_KEY set and differs from SECRET_KEY"),
        (bool(g("RESEND_API_KEY")) and bool(g("RESEND_FROM")), "RESEND_API_KEY and RESEND_FROM set"),
        ((g("HELIX_DISPATCH_INLINE") or "false").lower() not in TRUE, "HELIX_DISPATCH_INLINE false/unset"),
        ((g("AUTH_DEV_RESET_RETURN") or "false").lower() not in TRUE, "AUTH_DEV_RESET_RETURN false/unset"),
        (not (g("APIFY_ENABLED") or "").lower() == "true" or bool(g("APIFY_API_TOKEN")), "Apify off, or on with APIFY_API_TOKEN"),
        (bool(g("METAPI_API_KEY") or g("METAPI_KEY") or g("METAPI_TOKEN")), "METAPI_API_KEY set"),
        ((g("EMBEDDED_WORKER_ENABLED") or "").lower() == "true", "EMBEDDED_WORKER_ENABLED=true (free plan has no worker)"),
        ((g("USE_MOCKS") or "false").lower() not in TRUE, "USE_MOCKS false/unset"),
    ]
    return rows


async def db_checks(url: str) -> list[tuple[bool, str]]:
    import asyncpg

    parts = urlsplit(re.sub(r"^postgresql\+asyncpg://", "postgresql://", url))
    query = "&".join(q for q in parts.query.split("&") if q and not q.startswith("channel_binding="))
    dsn = parts._replace(query=query).geturl()
    host = (urlsplit(dsn).hostname or "").split(".")[0].replace("-pooler", "")
    rows = []
    try:
        c = await asyncpg.connect(dsn, timeout=30)
        await c.execute("SET default_transaction_read_only = on")
        branch = await c.fetchval("select current_setting('neon.branch_id', true)")
        role = await c.fetchrow("select current_user u, rolbypassrls b from pg_roles where rolname = current_user")
        app_m = await c.fetchval("select exists(select 1 from pg_roles where rolname='helix_app') and pg_has_role(current_user,'helix_app','MEMBER')")
        wrk_m = await c.fetchval("select exists(select 1 from pg_roles where rolname='helix_worker') and pg_has_role(current_user,'helix_worker','MEMBER')")
        rev = await c.fetchval("select version_num from alembic_version")
        await c.close()
    except Exception as exc:
        return [(False, f"DATABASE_URL could not be checked: {type(exc).__name__}")]
    rows.append((branch == LIVE_BRANCH and host == LIVE_ENDPOINT, f"DATABASE_URL is the live branch (server says branch {branch}, endpoint {host})"))
    rows.append((not role["b"], f"DATABASE_URL role {role['u']} does not bypass RLS"))
    rows.append((bool(app_m), f"DATABASE_URL role {role['u']} is a member of helix_app"))
    rows.append((bool(wrk_m), f"DATABASE_URL role {role['u']} is a member of helix_worker (embedded worker)"))
    rows.append((True, f"info: alembic revision = {rev}"))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--env-file", required=True)
    ap.add_argument("--no-db", action="store_true", help="skip the read-only database checks")
    args = ap.parse_args()
    env = load_env(args.env_file)
    rows = static_checks(env)
    if not args.no_db and env.get("DATABASE_URL"):
        rows += asyncio.run(db_checks(env["DATABASE_URL"]))
    elif not env.get("DATABASE_URL"):
        rows.append((False, "DATABASE_URL set"))
    for good, name in rows:
        print("OK  " if good else "FAIL", name)
    return 0 if all(good for good, _ in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
