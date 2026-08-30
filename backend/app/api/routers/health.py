from fastapi import APIRouter
from sqlalchemy import text
import asyncio
import os
from app.db.session import async_session_maker
from app.core.config import settings

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
        "GROQ_API_KEY": bool(settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")),
        "OPENROUTER_API_KEY": bool(settings.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY")),
        "GEMINI_API_KEY": bool(settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")),
        "SCRAPEGRAPH_API_KEY": bool(settings.SCRAPEGRAPH_API_KEY or os.getenv("SCRAPEGRAPH_API_KEY")),
        "META_ACCESS_TOKEN": bool(settings.META_ACCESS_TOKEN or os.getenv("META_ACCESS_TOKEN")),
        "BRIGHTDATA_API_KEY": bool(settings.BRIGHTDATA_API_KEY or os.getenv("BRIGHTDATA_API_KEY")),
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

