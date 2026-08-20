from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.deps import get_db

router = APIRouter()

@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        # Simple query to verify DB connection
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "db": "disconnected", "detail": str(e)}
