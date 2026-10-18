import asyncio
import datetime
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings, cors_origins
from app.db.session import engine, async_session_maker
from app.db.base import Base
from app.services.billing_service import refund, DISCOVER_SEARCH_CREDIT_COST
from app.middleware.rate_limit import RateLimitMiddleware
import app.models

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
    updates,
    providers,
    support,
    playbooks,
    dashboard,
    simulation,
    uploads,
    monitors,
    scout,
    leadgen,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.rls_role import assert_rls_role
    async with engine.begin() as conn:
        await assert_rls_role(conn)
    # Startup reconciliation. Jobs still marked active from a dead process lifetime
    # are reconciled. We check heartbeat_at < cutoff (or created_at < cutoff if no heartbeat
    # was recorded) to avoid terminating live jobs on other active workers.
    stuck_discover_jobs = []
    try:
        async with engine.begin() as conn:
            try:
                reconcile_cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
                reclaimable = """
                      AND NOT EXISTS (
                          SELECT 1 FROM work_items wi
                          WHERE wi.job_id = scrape_jobs.id
                            AND wi.status IN ('queued', 'leased')
                            AND wi.attempt_count < wi.max_attempts
                      )
                """
                stuck_discover_jobs = (await conn.execute(text(f"""
                    SELECT id, org_id FROM scrape_jobs
                    WHERE status IN ('queued', 'running')
                      AND (
                          (heartbeat_at IS NOT NULL AND heartbeat_at < :cutoff)
                          OR (heartbeat_at IS NULL AND created_at < :cutoff)
                      )
                      {reclaimable}
                """), {"cutoff": reconcile_cutoff})).mappings().all()
                if stuck_discover_jobs:
                    await conn.execute(text("""
                        UPDATE scrape_jobs
                        SET status = 'failed',
                            failure_kind = 'interrupted',
                            error_msg = 'Interrupted by a service restart — the credits for this search were refunded. Please run it again.'
                        WHERE status IN ('queued', 'running')
                          AND (
                              (heartbeat_at IS NOT NULL AND heartbeat_at < :cutoff)
                              OR (heartbeat_at IS NULL AND created_at < :cutoff)
                          )
                          AND NOT EXISTS (
                              SELECT 1 FROM work_items wi
                              WHERE wi.job_id = scrape_jobs.id
                                AND wi.status IN ('queued', 'leased')
                                AND wi.attempt_count < wi.max_attempts
                          )
                    """), {"cutoff": reconcile_cutoff})
                    print(f"Startup reconciliation: {len(stuck_discover_jobs)} stuck discover job(s) marked failed and refunded.")
                stuck_media_jobs = (await conn.execute(text("""
                    SELECT id FROM media_jobs
                    WHERE status IN ('pending', 'running', 'in_progress', 'processing')
                      AND (
                          (heartbeat_at IS NOT NULL AND heartbeat_at < :cutoff)
                          OR (heartbeat_at IS NULL AND created_at < :cutoff)
                      )
                      AND NOT EXISTS (
                          SELECT 1 FROM work_items wi
                          WHERE wi.job_id = media_jobs.id
                            AND wi.status IN ('queued', 'leased')
                            AND wi.attempt_count < wi.max_attempts
                      )
                """), {"cutoff": reconcile_cutoff})).all()
                if stuck_media_jobs:
                    await conn.execute(text("""
                        UPDATE media_jobs
                        SET status = 'failed',
                            failure_kind = 'interrupted',
                            error_message = 'Interrupted by a service restart. Please try generating again.'
                        WHERE status IN ('pending', 'running', 'in_progress', 'processing')
                          AND (
                              (heartbeat_at IS NOT NULL AND heartbeat_at < :cutoff)
                              OR (heartbeat_at IS NULL AND created_at < :cutoff)
                          )
                          AND NOT EXISTS (
                              SELECT 1 FROM work_items wi
                              WHERE wi.job_id = media_jobs.id
                                AND wi.status IN ('queued', 'leased')
                                AND wi.attempt_count < wi.max_attempts
                          )
                    """), {"cutoff": reconcile_cutoff})
                    print(f"Startup reconciliation: {len(stuck_media_jobs)} stuck media job(s) marked failed.")
            except Exception as reconcile_err:
                print("Startup reconciliation error:", reconcile_err)
    except Exception as e:
        print("Database startup reconciliation error:", e)

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

    # Heartbeat-aware sweep for jobs the age-only SQL pass above cannot see
    # yet (a restart that returns before the cutoff).
    reconciler = None
    try:
        from app.services.job_reconciliation import reconciliation_loop

        reconciler = asyncio.create_task(reconciliation_loop())
    except Exception as e:
        print("Job reconciliation startup error:", e)

    yield

    if reconciler:
        reconciler.cancel()

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
# Rate limiting: shields credential + expensive AI/scrape endpoints from
# brute-force and credit-burn bursts. Added after CORS so preflight OPTIONS
# requests are never throttled.
app.add_middleware(RateLimitMiddleware)

# Enterprise Security Headers Middleware
from starlette.requests import Request
from starlette.responses import Response

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

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
app.include_router(updates.router, prefix=f"{settings.API_V1_STR}/updates", tags=["updates"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(support.router, prefix=f"{settings.API_V1_STR}/support", tags=["support"])
app.include_router(playbooks.router, prefix=f"{settings.API_V1_STR}/playbooks", tags=["playbooks"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])
app.include_router(simulation.router, prefix=f"{settings.API_V1_STR}/simulation", tags=["simulation"])
app.include_router(health.router, prefix=f"{settings.API_V1_STR}/health", tags=["health"])
app.include_router(monitors.router, prefix=f"{settings.API_V1_STR}/monitors", tags=["monitors"])
app.include_router(scout.router, prefix=f"{settings.API_V1_STR}/scout", tags=["scout"])
app.include_router(scout.router, prefix="/api/v1/scout", tags=["scout"])
# Scout · Lead Generation (scrapling_engine worker) — separate router so Social/Atlas stays untouched
app.include_router(leadgen.router, prefix=f"{settings.API_V1_STR}/scout/leadgen", tags=["leadgen"])

# Locally stored media. This is served by a router rather than a StaticFiles
# mount so that access is checked: the old mount handed any file to anyone who
# could guess its name. Only reachable when R2 is unconfigured; see
# storage_service.
app.include_router(uploads.router, prefix="/uploads", tags=["uploads"])

@app.get("/")
@app.get("/api")
@app.get("/health")
@app.get("/api/health")
def root():
    return {
        "status": "ok",
        "service": "helix-backend",
        "message": "Welcome to Helix API. Service is online.",
    }
