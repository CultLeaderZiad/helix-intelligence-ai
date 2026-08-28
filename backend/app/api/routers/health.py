from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import os
from app.core.deps import get_db
from app.core.config import settings

router = APIRouter()

@router.get("")
@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "connected"
    db_error = None
    try:
        await db.execute(text("SELECT 1"))
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
        "USE_MOCKS": settings.USE_MOCKS
    }

    response = {
        "status": "ok" if db_status == "connected" else "error",
        "db": db_status,
        "env_vars": env_diagnostics
    }
    if db_error:
        response["detail"] = db_error
        
    return response
