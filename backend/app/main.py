import datetime
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings, cors_origins
from app.db.session import engine, async_session_maker
from app.db.base import Base
from app.services.billing_service import refund, DISCOVER_SEARCH_CREDIT_COST
import app.models

logger = logging.getLogger(__name__)

from app.api.routers import (
    auth,
    discover,
    creatives,
    analysis,
    admin,
    health,
    account,
    notifications,
    media,
    webhooks,
    updates,
    higgsfield,
    providers,
    support,
    playbooks,
    dashboard
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Loud, not silent: returning reset links from the API is a dev-only
    # convenience and the Blueprint pins it off, so anyone seeing this line in
    # production logs is looking at a deliberate override that should not exist.
    if settings.allow_reset_link_in_response:
        logger.warning(
            "AUTH_DEV_RESET_RETURN is ON (ENV=%s): password-reset links are being returned "
            "in API responses. Development only — turn it off before this reaches users.",
            settings.ENV,
        )

    # Ensure all database tables and missing columns exist on startup
    stuck_discover_jobs = []  # populated by the reconciliation sweep below
    try:
        async with engine.begin() as conn:
            # 1. Create all missing tables (e.g. support_tickets, support_ticket_replies, playbooks)
            await conn.run_sync(Base.metadata.create_all)

            # 2. Run non-destructive column migrations on existing PostgreSQL tables
            migrations = [
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS images_generated_today FLOAT DEFAULT 0.0;",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS videos_generated_today FLOAT DEFAULT 0.0;",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS images_today_date VARCHAR(32) DEFAULT '';",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS images_trial_total FLOAT DEFAULT 0.0;",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS custom_feature_flags JSON DEFAULT '{}'::json;",
                "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS status VARCHAR(64) DEFAULT 'active';",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS admin_permissions JSON DEFAULT '{}'::json;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_started_at TIMESTAMPTZ;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_expires_at TIMESTAMPTZ;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS has_completed_onboarding BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_token_hash VARCHAR;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_expires_at TIMESTAMPTZ;",
                "ALTER TABLE plans ADD COLUMN IF NOT EXISTS daily_image_limit INTEGER DEFAULT 5;",
                "ALTER TABLE plans ADD COLUMN IF NOT EXISTS daily_video_limit INTEGER DEFAULT 3;",
                "ALTER TABLE plans ADD COLUMN IF NOT EXISTS price_monthly FLOAT DEFAULT 0.0;",
            ]
            for query in migrations:
                try:
                    await conn.execute(text(query))
                except Exception as col_err:
                    pass

            # Structural duplicate-search guard. The service-level check
            # above is advisory; this makes a second active job for the same
            # (org, normalized query) impossible at the database level.
            # Failures here are reported, not swallowed — a silently missing
            # unique index would resurrect the double-charge race.
            try:
                await conn.execute(text("""
                    UPDATE scrape_jobs AS newer
                    SET status = 'failed',
                        error_msg = 'Duplicate of a concurrent search for the same query (collapsed by dedup guard migration)'
                    WHERE newer.status IN ('queued', 'running')
                      AND EXISTS (
                        SELECT 1 FROM scrape_jobs AS older
                        WHERE older.status IN ('queued', 'running')
                          AND older.org_id = newer.org_id
                          AND lower(older.query) = lower(newer.query)
                          AND (older.created_at, older.id) < (newer.created_at, newer.id)
                      )
                """))
                await conn.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_scrape_jobs_active_query
                    ON scrape_jobs (org_id, lower(query))
                    WHERE status IN ('queued', 'running')
                """))
            except Exception as dup_guard_err:
                print("Duplicate-search guard migration error:", dup_guard_err)

            # Startup reconciliation. Jobs still marked active from a previous
            # process lifetime are dead — this process cannot resume them.
            # Mark them failed with an honest reason so clients stop polling a
            # corpse; discover jobs additionally get their upfront charge
            # refunded (the user paid for a result they will never receive).
            try:
                reconcile_cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
                stuck_discover_jobs = (await conn.execute(text("""
                    SELECT id, org_id FROM scrape_jobs
                    WHERE status IN ('queued', 'running')
                      AND created_at < :cutoff
                """), {"cutoff": reconcile_cutoff})).mappings().all()
                if stuck_discover_jobs:
                    await conn.execute(text("""
                        UPDATE scrape_jobs
                        SET status = 'failed',
                            error_msg = 'Interrupted by a service restart — the credits for this search were refunded. Please run it again.'
                        WHERE status IN ('queued', 'running')
                          AND created_at < :cutoff
                    """), {"cutoff": reconcile_cutoff})
                    print(f"Startup reconciliation: {len(stuck_discover_jobs)} stuck discover job(s) marked failed and refunded.")
                stuck_media_jobs = (await conn.execute(text("""
                    SELECT id FROM media_jobs
                    WHERE status IN ('pending', 'running', 'in_progress', 'processing')
                      AND created_at < :cutoff
                """), {"cutoff": reconcile_cutoff})).all()
                if stuck_media_jobs:
                    await conn.execute(text("""
                        UPDATE media_jobs
                        SET status = 'failed',
                            error_message = 'Interrupted by a service restart. Please try generating again.'
                        WHERE status IN ('pending', 'running', 'in_progress', 'processing')
                          AND created_at < :cutoff
                    """), {"cutoff": reconcile_cutoff})
                    print(f"Startup reconciliation: {len(stuck_media_jobs)} stuck media job(s) marked failed.")
            except Exception as reconcile_err:
                print("Startup reconciliation error:", reconcile_err)
    except Exception as e:
        print("Database startup sync error:", e)

    # Refunds run after the migration transaction commits, each in its own
    # locked session (the same primitive the discover pipeline uses).
    for row in stuck_discover_jobs:
        try:
            async with async_session_maker() as sweep_db:
                await refund(
                    sweep_db,
                    row["org_id"],
                    DISCOVER_SEARCH_CREDIT_COST,
                    "service_restart_sweep",
                    row["id"],
                )
        except Exception as refund_err:
            print(f"Startup reconciliation refund failed for job {row['id']}:", refund_err)

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set all CORS enabled origins
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(account.router, prefix=f"{settings.API_V1_STR}/account", tags=["account"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_STR}/notifications", tags=["notifications"])
app.include_router(discover.router, prefix=f"{settings.API_V1_STR}/discovery", tags=["discovery"])
app.include_router(creatives.router, prefix=f"{settings.API_V1_STR}/creatives", tags=["creatives"])
app.include_router(creatives.brands_router, prefix=f"{settings.API_V1_STR}/brands", tags=["brands"])
app.include_router(creatives.patterns_router, prefix=f"{settings.API_V1_STR}/patterns", tags=["patterns"])
app.include_router(analysis.insights_router, prefix=f"{settings.API_V1_STR}/insights", tags=["insights"])
app.include_router(media.router, prefix=f"{settings.API_V1_STR}/media", tags=["media"])
app.include_router(providers.router, prefix=f"{settings.API_V1_STR}", tags=["providers"])
app.include_router(webhooks.router, prefix=f"{settings.API_V1_STR}/webhooks", tags=["webhooks"])
app.include_router(updates.router, prefix=f"{settings.API_V1_STR}/updates", tags=["updates"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(support.router, prefix=f"{settings.API_V1_STR}/support", tags=["support"])
app.include_router(playbooks.router, prefix=f"{settings.API_V1_STR}/playbooks", tags=["playbooks"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])
app.include_router(health.router, prefix=f"{settings.API_V1_STR}/health", tags=["health"])
app.include_router(higgsfield.router, prefix=f"{settings.API_V1_STR}/higgsfield", tags=["higgsfield"])
app.include_router(higgsfield.router, prefix="/higgsfield", tags=["higgsfield"])

# Mount uploads directory for serving static files
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/")
@app.get("/health")
def root():
    return {
        "status": "ok",
        "service": "helix-backend",
        "message": "Welcome to Helix API. Service is online.",
    }
