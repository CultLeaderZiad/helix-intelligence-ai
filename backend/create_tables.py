import asyncio
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import engine
from app.db.base import Base
import app.models

async def init_db():
    print("Connecting to Neon Postgres...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables (including app_updates) successfully created/verified!")

if __name__ == "__main__":
    asyncio.run(init_db())
