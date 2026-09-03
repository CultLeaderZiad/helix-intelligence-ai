"""
Owner recovery tool: set a known password (and admin role) for an account.

Use this when you are locked out and the self-service reset flow is not
deployed yet:

    cd backend
    python scripts/reset_admin_password.py \
        --email you@gmail.com \
        --password 'YourNewStrongPassword!'

The password can also come from the ADMIN_EMAIL / ADMIN_PASSWORD env vars
so it never ends up in shell history or git.

Connects with the same DATABASE_URL that the API uses; run it on a machine
that has access to that database (local .env.local or Render shell).
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from sqlalchemy import select, func
from app.db.session import async_session_maker
from app.models.user import User
from app.core.security import get_password_hash


def parse_args():
    parser = argparse.ArgumentParser(description="Reset a user's password (optionally promote to admin).")
    parser.add_argument("--email", default=os.environ.get("ADMIN_EMAIL"), help="Account email (or ADMIN_EMAIL env).")
    parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD"), help="New password (or ADMIN_PASSWORD env).")
    parser.add_argument("--role", default="admin", help="Role to set (default: admin).")
    parser.add_argument("--create", action="store_true", help="Create the user if they do not exist.")
    return parser.parse_args()


async def main():
    args = parse_args()
    if not args.email or not args.password:
        sys.exit("ERROR: --email and --password are required (or set ADMIN_EMAIL / ADMIN_PASSWORD).")
    if len(args.password) < 8:
        sys.exit("ERROR: password must be at least 8 characters.")

    email = args.email.strip().lower()
    async with async_session_maker() as db:
        result = await db.execute(select(User).where(func.lower(User.email) == email))
        user = result.scalar_one_or_none()

        if user:
            user.password_hash = get_password_hash(args.password)
            user.role = args.role
            user.password_reset_token_hash = None
            user.password_reset_expires_at = None
            print(f"Updated existing user {user.email} (id={user.id}) role -> {args.role}.")
        elif args.create:
            user = User(
                email=email,
                password_hash=get_password_hash(args.password),
                role=args.role,
                has_completed_onboarding=True,
            )
            db.add(user)
            print(f"Created user {email} with role {args.role}.")
        else:
            sys.exit(f"ERROR: no user found for {email}. Re-run with --create to create the account.")

        await db.commit()
        print(f"SUCCESS: password updated for {email}. You can now sign in.")

if __name__ == "__main__":
    asyncio.run(main())
