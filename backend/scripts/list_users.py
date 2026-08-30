import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.db.session import async_session_maker
from app.models.user import User
from sqlalchemy import select

async def main():
    async with async_session_maker() as db:
        res = await db.execute(select(User.id, User.email, User.role))
        users = res.all()
        print("Database Users:")
        for u in users:
            print(f"- ID: {u[0]} | Email: {u[1]} | Role: {u[2]}")

if __name__ == "__main__":
    asyncio.run(main())
