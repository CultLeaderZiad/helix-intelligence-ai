import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.db.session import async_session_maker
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import update, select

async def reset_admin_password():
    email = "cultleaderzoz.dev@gmail.com"
    new_password = "HelixAdmin2026!"
    hashed_pwd = get_password_hash(new_password)

    async with async_session_maker() as db:
        res = await db.execute(select(User).where(User.email == email))
        user = res.scalar_one_or_none()

        if user:
            user.password_hash = hashed_pwd
            user.role = "admin"
            user.has_completed_onboarding = True
            print(f"Updated existing user {email} to admin with new password.")
        else:
            user = User(
                email=email,
                password_hash=hashed_pwd,
                role="admin",
                has_completed_onboarding=True
            )
            db.add(user)
            print(f"Created new user {email} as admin with new password.")

        await db.commit()
        print(f"SUCCESS: Password for {email} has been reset to: {new_password}")

if __name__ == "__main__":
    asyncio.run(reset_admin_password())
