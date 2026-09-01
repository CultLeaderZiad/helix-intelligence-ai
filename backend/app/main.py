import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings, cors_origins
from app.db.session import engine
from app.db.base import Base
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
    # Ensure all database tables and missing columns exist on startup
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
                "ALTER TABLE plans ADD COLUMN IF NOT EXISTS daily_image_limit INTEGER DEFAULT 5;",
                "ALTER TABLE plans ADD COLUMN IF NOT EXISTS daily_video_limit INTEGER DEFAULT 3;",
                "ALTER TABLE plans ADD COLUMN IF NOT EXISTS price_monthly FLOAT DEFAULT 0.0;",
            ]
            for query in migrations:
                try:
                    await conn.execute(text(query))
                except Exception as col_err:
                    pass
    except Exception as e:
        print("Database startup sync error:", e)
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
