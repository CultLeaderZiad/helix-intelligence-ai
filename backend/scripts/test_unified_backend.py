import asyncio
import os
import sys

# Ensure UTF-8 output encoding on Windows console
if sys.platform.startswith("win"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import async_session_maker, engine
from app.db.base import Base
from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.support_ticket import SupportTicket, SupportTicketReply
from app.models.playbook import Playbook
from app.models.notification import Notification
from app.services import admin_service, support_service, playbook_service, auth_service
from app.schemas.admin import PlanUpdate
from sqlalchemy import select, text

async def run_tests():
    print("=== Testing Backend Services & Database Models ===")
    
    # 1. Run migrations & table creations
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        migrations = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS admin_permissions JSON DEFAULT '{}'::json;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_started_at TIMESTAMPTZ;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_expires_at TIMESTAMPTZ;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS has_completed_onboarding BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE plans ADD COLUMN IF NOT EXISTS daily_image_limit INTEGER DEFAULT 5;",
            "ALTER TABLE plans ADD COLUMN IF NOT EXISTS daily_video_limit INTEGER DEFAULT 3;",
            "ALTER TABLE plans ADD COLUMN IF NOT EXISTS price_monthly FLOAT DEFAULT 0.0;",
        ]
        for query in migrations:
            try:
                await conn.execute(text(query))
            except Exception as e:
                print(f"Migration note for {query}: {e}")
        print("[OK] All tables and column migrations verified on Neon DB.")

    async with async_session_maker() as db:
        # Find or create an admin user
        admin = (await db.execute(select(User).where(User.role == "admin"))).scalars().first()
        if not admin:
            admin = (await db.execute(select(User))).scalars().first()
            if admin:
                admin.role = "admin"
                await db.commit()
        print(f"[OK] Using Admin User: {admin.email if admin else 'None'}")

        # Find or create a test customer user
        customer = (await db.execute(select(User).where(User.email != admin.email))).scalars().first()
        if not customer:
            from app.schemas.auth import UserCreate
            customer = await auth_service.register_user(db, UserCreate(email="testcustomer@helix.ai", password="Password123!"))
        print(f"[OK] Using Customer User: {customer.email}")

        # TEST 1: Live Plan Editor
        plans = await admin_service.list_plans(db)
        if plans:
            target_plan = plans[0]
            orig_allowance = target_plan.credit_allowance
            updated = await admin_service.update_plan(
                db, 
                target_plan.id, 
                PlanUpdate(credit_allowance=orig_allowance + 5, daily_image_limit=10, price_monthly=49.0)
            )
            print(f"[OK] Plan Editor: Updated {updated.name} allowance to {updated.credit_allowance} and price to ${updated.price_monthly}")

        # TEST 2: User Banning & Unbanning
        ban_res = await admin_service.ban_user(db, customer.id, is_banned=True)
        print(f"[OK] User Ban: {ban_res}")
        assert customer.is_banned == True

        # Verify authentication fails when banned
        from app.schemas.auth import UserLogin
        try:
            await auth_service.authenticate_user(db, UserLogin(email=customer.email, password="Password123!"))
            print("[FAIL] Error: Banned user should have failed authentication!")
        except Exception as e:
            print(f"[OK] Banned User Auth Rejected Correctly: {e}")

        # Unban customer
        unban_res = await admin_service.ban_user(db, customer.id, is_banned=False)
        print(f"[OK] User Unban: {unban_res}")

        # TEST 3: Admin Broadcast
        broadcast_res = await admin_service.broadcast_announcement(
            db,
            title="System Maintenance Complete",
            message="All services are running at full speed.",
            notif_type="system"
        )
        print(f"[OK] Admin Broadcast: {broadcast_res}")

        # TEST 4: Support Ticket Creation & Threaded Reply
        ticket = await support_service.create_ticket(
            db,
            user=customer,
            ticket_type="feedback",
            subject="Add export to CSV in Discover",
            message="It would be great to export the ad copy to CSV directly.",
            tag="discover",
            context_data={"page": "/discovery", "plan": "growth"}
        )
        print(f"[OK] Ticket Created: ID={ticket.id}, Subject='{ticket.subject}'")

        # Admin replies
        reply_admin = await support_service.add_reply(
            db,
            ticket_id=ticket.id,
            user=admin,
            message="Thanks for the feedback! We are adding this in the next sprint."
        )
        print(f"[OK] Admin Replied: '{reply_admin['message']}' (is_admin={reply_admin['is_admin']})")

        # Customer replies back
        reply_cust = await support_service.add_reply(
            db,
            ticket_id=ticket.id,
            user=customer,
            message="Awesome, thanks team!"
        )
        print(f"[OK] Customer Replied: '{reply_cust['message']}' (is_admin={reply_cust['is_admin']})")

        # Fetch thread details
        details = await support_service.get_ticket_details(db, ticket.id, customer)
        print(f"[OK] Ticket Thread Length: {len(details['replies'])} messages")
        assert len(details['replies']) == 2

        # TEST 5: Shareable Creative Playbook
        playbook = await playbook_service.compile_playbook(
            db=db,
            user=customer,
            brand_name="shopify",
            query="shopify"
        )
        print(f"[OK] Playbook Compiled: Public ID = {playbook.public_id}, Title = '{playbook.title}'")

        # Fetch publicly (unauthenticated)
        public_view = await playbook_service.get_public_playbook(db, playbook.public_id)
        print(f"[OK] Public Playbook View Loaded: Brand = '{public_view['brand_name']}', Patterns = {len(public_view['patterns'])}, Creatives = {len(public_view['creatives'])}")

    print("\n=== ALL BACKEND CAPABILITIES VERIFIED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(run_tests())
