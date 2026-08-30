import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.db.session import async_session_maker
from app.models.user import User
from sqlalchemy import update, select

async def main():
    admin_emails = [
        "cultleaderzoz.dev@gmail.com",
        "ziad@vhynex.com",
        "ziad_test@vynex.com",
        "admin@example.com",
    ]
    async with async_session_maker() as db:
        await db.execute(
            update(User)
            .where(User.email.in_(admin_emails))
            .values(role="admin")
        )
        await db.commit()

        res = await db.execute(select(User.email, User.role).where(User.role == "admin"))
        print("Active Admin Accounts:")
        for r in res.all():
            print(f"  • {r[0]} ({r[1]})")

if __name__ == "__main__":
    asyncio.run(main())
