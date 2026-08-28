import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))

from app.db.session import async_session_maker
from sqlalchemy import text

async def query_users():
    async with async_session_maker() as db:
        try:
            result = await db.execute(text("SELECT id, email, role FROM users LIMIT 10"))
            rows = result.fetchall()
            print("Users in DB:", rows)
        except Exception as e:
            print("DB Error:", e)

if __name__ == "__main__":
    asyncio.run(query_users())
