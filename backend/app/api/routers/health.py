from fastapi import APIRouter, Header, Response, status
from typing import Optional
from sqlalchemy import text, select
import asyncio
import os
import hmac
from app.db.session import async_session_maker
from app.core.config import settings
from app.core.credentials import env_secret
from app.models.user import User

import logging
from app.core.observability import log_event

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/live")
async def liveness():
    """Liveness probe: verifies process is alive and accepting traffic."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness(response: Response):
    """Readiness probe: verifies database connection and representative ORM query."""
    try:
        async def _check_db():
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))
                await session.execute(select(User.id).limit(1))

        await asyncio.wait_for(_check_db(), timeout=3.0)
        return {"status": "ready", "database": "connected"}
    except (asyncio.TimeoutError, TimeoutError):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unready", "database": "timeout", "detail": "Database ping timed out"}
    except Exception as exc:
        log_event(logger, "readiness_database_failed", error=exc)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unready", "database": "disconnected", "code": "database_unavailable", "detail": "Database is unavailable"}


@router.get("")
@router.get("/")
async def health_check(
    response: Response,
    x_admin_secret: Optional[str] = Header(None, alias="X-Admin-Secret"),
):
    db_status = "unknown"
    db_error = None
    try:
        async def _ping_db():
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))
                await session.execute(select(User.id).limit(1))

        await asyncio.wait_for(_ping_db(), timeout=3.0)
        db_status = "connected"
    except (asyncio.TimeoutError, TimeoutError):
        db_status = "timeout"
        db_error = "Database ping timed out"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    except Exception as exc:
        log_event(logger, "health_database_failed", error=exc)
        db_status = "disconnected"
        db_error = "Database is unavailable"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    # Strictly protect internal API presence diagnostics: only return when authenticated with admin secret
    diagnostic_key = settings.HEALTH_DIAGNOSTIC_KEY
    is_admin_req = bool(
        diagnostic_key
        and diagnostic_key != settings.SECRET_KEY
        and x_admin_secret
        and hmac.compare_digest(x_admin_secret.encode(), diagnostic_key.encode())
    )

    res = {
        "status": "ok" if db_status == "connected" else "degraded",
        "service": "helix-backend",
        "db": db_status,
    }
    if db_error and is_admin_req:
        res["db_detail"] = db_error
    if is_admin_req:
        res["env_vars"] = {
            "DATABASE_URL": bool(settings.DATABASE_URL or os.getenv("DATABASE_URL")),
            "GROQ_API_KEY": bool(env_secret("GROQ_API_KEY", fallback=settings.GROQ_API_KEY)),
            "OPENROUTER_API_KEY": bool(env_secret("OPENROUTER_API_KEY", fallback=settings.OPENROUTER_API_KEY)),
            "GEMINI_API_KEY": bool(env_secret("GEMINI_API_KEY", fallback=settings.GEMINI_API_KEY)),
            "SCRAPEGRAPH_API_KEY": bool(env_secret("SCRAPEGRAPH_API_KEY", fallback=settings.SCRAPEGRAPH_API_KEY)),
            "METAPI_API_KEY": bool(env_secret("METAPI_API_KEY", "METAPI_KEY", "METAPI_TOKEN", "Meta_Api", "META_API", "meta_api", fallback=settings.METAPI_API_KEY)),
            "ADYNTEL_API_KEY": bool(env_secret("ADYNTEL_API_KEY", fallback=settings.ADYNTEL_API_KEY)),
            "META_ACCESS_TOKEN": bool(env_secret("META_ACCESS_TOKEN", fallback=settings.META_ACCESS_TOKEN)),
            "BRIGHTDATA_API_KEY": bool(env_secret("BRIGHTDATA_API_KEY", fallback=settings.BRIGHTDATA_API_KEY)),
            "APIFY_API_TOKEN": bool(env_secret("APIFY_API_TOKEN", "APIFY_TOKEN", fallback=settings.APIFY_API_TOKEN)),
            "APIFY_ENABLED": bool(settings.APIFY_ENABLED),
            "JWT_SECRET": bool(settings.SECRET_KEY or os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET")),
            "USE_MOCKS": settings.USE_MOCKS,
        }

    return res
