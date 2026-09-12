import asyncio
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv("backend/.env")

from app.db.session import async_session_maker
from app.models.user import User
from app.services import admin_service, support_service
from app.schemas.admin import PlanUpdate
from sqlalchemy import select

async def main():
    print("=" * 80)
    print("ADMIN CENTER LIVE SUITE TEST")
    print("=" * 80)

    async with async_session_maker() as db:
        admin = (await db.execute(select(User).where(User.role == "admin").limit(1))).scalar_one_or_none()
        test_user = (await db.execute(select(User).where(User.role != "admin").limit(1))).scalar_one_or_none()
        print(f"Admin: {admin.email}")
        print(f"Target User: {test_user.email}")

        # 1. Plan Editing
        print("\n--- [1] PLAN EDITING ---")
        plans = await admin_service.list_plans(db)
        print(f"Available plans ({len(plans)}): {[p.id for p in plans]}")
        target_plan = plans[0]
        orig_price = target_plan.price_monthly
        # Test updating plan
        up_data = PlanUpdate(price_monthly=orig_price)
        updated = await admin_service.update_plan(db, target_plan.id, up_data)
        print(f"Plan '{updated.id}' successfully updated (price_monthly: {updated.price_monthly})")

        # 2. User Ban / Status
        print("\n--- [2] USER BAN & UNBAN ---")
        ban_res = await admin_service.ban_user(db, test_user.id, is_banned=True)
        print(f"User {test_user.email} banned: status={ban_res.get('status')}")
        unban_res = await admin_service.ban_user(db, test_user.id, is_banned=False)
        print(f"User {test_user.email} unbanned: status={unban_res.get('status')}")

        # 3. Per-User Usage Visibility
        print("\n--- [3] PER-USER USAGE LOGS ---")
        user_logs = await admin_service.get_usage_logs_filtered(db, user_id=test_user.id, page=1, page_size=5)
        print(f"Usage logs found for {test_user.email}: total={user_logs.total_count}, items count={len(user_logs.items)}")
        if user_logs.items:
            first_log = user_logs.items[0]
            print(f"Sample log: Op={first_log.operation}, Provider={first_log.provider}, Cost={first_log.cost_usd}, Deducted={first_log.credits_deducted}")

        # 4. Broadcast Notifications
        print("\n--- [4] BROADCAST NOTIFICATIONS ---")
        b_res = await admin_service.broadcast_announcement(
            db,
            title="System Performance Test Notice",
            message="Helix verification complete. High accuracy operational.",
            notif_type="system",
            link="/dashboard"
        )
        print(f"Broadcast success: {b_res.get('message')}, recipients={b_res.get('recipients_count')}")

        # 5. Support Ticket Handling
        print("\n--- [5] SUPPORT TICKET HANDLING ---")
        ticket = await support_service.create_ticket(
            db,
            user=test_user,
            ticket_type="feedback",
            subject="Test Admin Verification Ticket",
            message="Verifying admin ticket response flow.",
            tag="discover"
        )
        print(f"Created ticket ID: {ticket.id}, Status: {ticket.status}")
        # Admin views ticket
        admin_tickets = await support_service.list_admin_tickets(db)
        found = [t for t in admin_tickets if t["id"] == ticket.id]
        print(f"Ticket visible in Admin queue: {bool(found)}")
        # Admin replies to ticket
        reply_res = await support_service.add_reply(db, ticket.id, admin, "We are verifying this ticket live.")
        print(f"Admin replied: reply_id={reply_res.get('reply', {}).get('id')}")
        # Admin resolves ticket
        status_res = await support_service.update_ticket_status(db, ticket.id, "resolved")
        print(f"Ticket resolved: new_status={status_res.get('ticket', {}).get('status')}")

        # 6. Cross-User Credit / API Consumption Data
        print("\n--- [6] CROSS-USER USAGE & API SUMMARY ---")
        summary = await admin_service.get_usage_summary(db)
        print(f"Total Requests: {summary.total_requests}")
        print(f"Total Credits Deducted across all users: {summary.total_credits_deducted}")
        print(f"Total Provider Cost (USD): ${summary.total_cost_usd:.4f}")
        print(f"Breakdown by Provider: {[b.provider for b in summary.by_provider]}")
        print(f"Recent Logs Count: {len(summary.recent_logs)}")

if __name__ == "__main__":
    asyncio.run(main())
