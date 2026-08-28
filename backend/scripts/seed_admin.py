import asyncio
import os
import sys

# Ensure backend directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))

from app.db.session import async_session_maker
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def seed_admin():
    async with async_session_maker() as db:
        email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
        password = os.environ.get("ADMIN_PASSWORD", "password123")
        
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        # `get_password_hash` might be sync or async. Usually sync. Let's assume it's sync, wait, let me check core/security.py if needed.
        # It's usually sync for passlib.
        try:
            pwd_hash = await get_password_hash(password)
        except TypeError:
            pwd_hash = get_password_hash(password)
            
        if user:
            print(f"User {email} already exists. Updating role to admin.")
            user.role = "admin"
            user.password_hash = pwd_hash
        else:
            print(f"Creating new admin user: {email}")
            user = User(
                email=email,
                password_hash=pwd_hash,
                role="admin",
                has_completed_onboarding=True
            )
            db.add(user)
        
        await db.commit()
        print("Admin user seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed_admin())
