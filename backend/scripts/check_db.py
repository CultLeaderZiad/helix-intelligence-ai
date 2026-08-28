import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))

from app.db.session import async_session_maker
from sqlalchemy import text

async def check_db():
    async with async_session_maker() as db:
        try:
            result = await db.execute(text("SELECT trial_started_at FROM users LIMIT 1"))
            print("Columns exist:", result.fetchall())
        except Exception as e:
            print("DB Error:", e)

if __name__ == "__main__":
    asyncio.run(check_db())
