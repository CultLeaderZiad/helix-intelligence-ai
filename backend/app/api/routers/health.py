from fastapi import APIRouter
from sqlalchemy import text
import asyncio
import os
from app.db.session import async_session_maker
from app.core.config import settings
from app.core.credentials import env_secret

router = APIRouter()

@router.get("")
@router.get("/")
async def health_check():
    db_status = "unknown"
    db_error = None
    try:
        async def _ping_db():
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))

        # Strict 2.5s timeout: return fast 200 OK even if Neon is cold starting
        await asyncio.wait_for(_ping_db(), timeout=2.5)
        db_status = "connected"
    except (asyncio.TimeoutError, TimeoutError):
        db_status = "waking_up"
        db_error = "Database ping timed out (Neon sleeping / cold starting)"
    except Exception as e:
        db_status = "disconnected"
        db_error = str(e)

    # Safe presence indicators (boolean True/False)
    env_diagnostics = {
        "DATABASE_URL": bool(settings.DATABASE_URL or os.getenv("DATABASE_URL")),
        "GROQ_API_KEY": bool(env_secret("GROQ_API_KEY", fallback=settings.GROQ_API_KEY)),
        "OPENROUTER_API_KEY": bool(env_secret("OPENROUTER_API_KEY", fallback=settings.OPENROUTER_API_KEY)),
        "GEMINI_API_KEY": bool(env_secret("GEMINI_API_KEY", fallback=settings.GEMINI_API_KEY)),
        "SCRAPEGRAPH_API_KEY": bool(env_secret("SCRAPEGRAPH_API_KEY", fallback=settings.SCRAPEGRAPH_API_KEY)),
        "METAPI_API_KEY": bool(env_secret("METAPI_API_KEY", "METAPI_KEY", "METAPI_TOKEN", fallback=settings.METAPI_API_KEY)),
        "ADYNTEL_API_KEY": bool(env_secret("ADYNTEL_API_KEY", fallback=settings.ADYNTEL_API_KEY)),
        "META_ACCESS_TOKEN": bool(env_secret("META_ACCESS_TOKEN", fallback=settings.META_ACCESS_TOKEN)),
        "BRIGHTDATA_API_KEY": bool(env_secret("BRIGHTDATA_API_KEY", fallback=settings.BRIGHTDATA_API_KEY)),
        "APIFY_API_TOKEN": bool(env_secret("APIFY_API_TOKEN", "APIFY_TOKEN", fallback=settings.APIFY_API_TOKEN)),
        "APIFY_ENABLED": bool(settings.APIFY_ENABLED),
        "JWT_SECRET": bool(settings.SECRET_KEY or os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET")),
        "USE_MOCKS": settings.USE_MOCKS,
    }

    response = {
        "status": "ok",
        "service": "helix-backend",
        "db": db_status,
        "env_vars": env_diagnostics,
    }
    if db_error:
        response["db_detail"] = db_error

    return response

