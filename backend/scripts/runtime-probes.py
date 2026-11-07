"""Synthetic access probes, never migration/RLS/deployment evidence.

Requires a newly-created, empty local PostgreSQL database named
``helix_w4_probe_*``, ENVIRONMENT=test and explicit disposable-DB consent.
No schema or data is dropped. Do not point this at a shared test database.
"""
import asyncio
import datetime
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit


def require_disposable_database():
    """Fail before application imports or any database/network operations."""
    if os.getenv("HELIX_ALLOW_DISPOSABLE_PROBES") != "yes":
        raise RuntimeError("Set HELIX_ALLOW_DISPOSABLE_PROBES=yes only for an isolated disposable database")
    if os.getenv("ENVIRONMENT") != "test":
        raise RuntimeError("Runtime probes require ENVIRONMENT=test")
    url = urlsplit(os.getenv("DATABASE_URL", ""))
    database = url.path.lstrip("/")
    if (url.scheme not in {"postgresql", "postgresql+asyncpg"}
            or url.hostname not in {"localhost", "127.0.0.1", "::1"}
            or url.query or url.fragment
            or not database.startswith("helix_w4_probe_")
            or not database.removeprefix("helix_w4_probe_")):
        raise RuntimeError("Runtime probes require an explicitly named local helix_w4_probe_* database")


async def main():
    require_disposable_database()
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
    import httpx
    from sqlalchemy import text
    from app.db.session import engine, async_session_maker
    from app.models import Base
    from app.models.user import User
    from app.models.organization import Organization
    from app.models.scrape_job import ScrapeJob
    from app.models.creative import Creative
    from app.core.security import get_password_hash, create_access_token
    from app.main import app

    try:
        async with engine.begin() as connection:
            tables = await connection.scalar(text(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
            ))
            if tables:
                raise RuntimeError("Runtime probes refuse a nonempty database; create a new disposable database")
            # Diagnostic fixture only: this deliberately does NOT validate migrations.
            await connection.run_sync(Base.metadata.create_all)
        now = datetime.datetime.now(datetime.timezone.utc)
        async with async_session_maker() as db:
            db.add_all([
                User(id="probe-alice", email="alice@example.invalid", password_hash="EXTERNAL_AUTH_MANAGED", trial_expires_at=now + datetime.timedelta(days=7)),
                User(id="probe-bob", email="bob@example.invalid", password_hash=get_password_hash("SyntheticProbe123!"), trial_expires_at=now + datetime.timedelta(days=7)),
            ])
            await db.flush()
            db.add_all([
                Organization(id="probe-oa", name="Synthetic A", owner_id="probe-alice"),
                Organization(id="probe-ob", name="Synthetic B", owner_id="probe-bob"),
            ])
            await db.flush()
            db.add(ScrapeJob(id="probe-private-job", org_id="probe-oa", query="synthetic", status="succeeded", created_at=now))
            await db.flush()
            db.add(Creative(id="probe-private-creative", job_id="probe-private-job", platform="meta", format="image", headline="Synthetic private content"))
            await db.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://local") as client:
            result = await client.post("/api/auth/sign-in", json={"email": "alice@example.invalid", "password": "EXTERNAL_AUTH_MANAGED"})
            assert result.status_code == 401, "External authentication marker must not be a password"
            print("sentinel_login: rejected")
            headers = {"Authorization": "Bearer " + create_access_token("probe-bob")}
            for path in ["/api/creatives/probe-private-creative", "/api/creatives/probe-private-creative/save"]:
                result = await (client.post(path, headers=headers) if path.endswith("/save") else client.get(path, headers=headers))
                assert result.status_code in {401, 403, 404}, "Foreign content access was not rejected"
                print("foreign_access: rejected", result.status_code)
        print("Synthetic application access probes passed; migrations and RLS were not exercised.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
