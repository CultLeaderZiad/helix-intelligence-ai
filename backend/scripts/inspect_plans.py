import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv("backend/.env")

from app.db.session import async_session_maker
from app.models.plan import Plan
from sqlalchemy import select

async def main():
    async with async_session_maker() as db:
        plans = (await db.execute(select(Plan))).scalars().all()
        for p in plans:
            print(f"ID: {p.id} | Name: '{p.name}' | Type: {p.type} | Monthly Price: ${p.price_monthly} | Allowance: {p.credit_allowance} credits | Price/Credit: ${p.price_per_credit}")

if __name__ == "__main__":
    asyncio.run(main())
