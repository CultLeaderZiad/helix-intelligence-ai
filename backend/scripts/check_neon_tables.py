import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv("backend/.env")

from app.db.session import async_session_maker
from sqlalchemy import text

async def check():
    async with async_session_maker() as db:
        res = await db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = [r[0] for r in res.fetchall()]
        print("Neon DB Tables:", sorted(tables))
        
        # Check monitors table columns
        if 'monitors' in tables:
            m_res = await db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='monitors'"))
            print("Monitors columns:", [r[0] for r in m_res.fetchall()])
        else:
            print("WARNING: 'monitors' table does NOT exist in Neon DB!")

        # Check simulation_reports table
        if 'simulation_reports' in tables:
            print("simulation_reports table exists.")
        else:
            print("WARNING: 'simulation_reports' table does NOT exist in Neon DB!")

if __name__ == "__main__":
    asyncio.run(check())
