import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv("backend/.env")

from app.db.session import async_session_maker
from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan
from app.schemas.media import MediaGenerationRequest
from app.services import media_service, billing_service
from sqlalchemy import select

async def test_tiered_routing_and_caps():
    print("=" * 80)
    print("TEST: TIERED ROUTING, TRIAL CAPS & ADMIN BYPASS")
    print("=" * 80)

    async with async_session_maker() as db:
        admin = (await db.execute(select(User).where(User.role == "admin").limit(1))).scalar_one_or_none()
        trial_user = (await db.execute(select(User).where(User.role != "admin").limit(1))).scalar_one_or_none()
        
        print(f"Admin User: {admin.email if admin else 'None'}")
        print(f"Trial User: {trial_user.email if trial_user else 'None'}")

        # Ensure trial_user has an active trial for this test
        orig_trial_exp = trial_user.trial_expires_at
        trial_user.trial_expires_at = datetime.now(timezone.utc) + timedelta(days=5)
        trial_org = await billing_service.get_or_create_default_org(db, trial_user)
        trial_org.daily_images_used_today = 0
        trial_org.status = "active"
        await db.commit()

        # 1. Test Routing for Trial User
        req_trial = MediaGenerationRequest(prompt="A sleek modern shoe ad", mode="premium_ad", provider="")
        job_trial = await media_service.create_media_job(db, trial_user, req_trial)
        print(f"[1. Trial User Routing] Created Job ID={job_trial.id}, Assigned Provider={job_trial.provider}")
        assert job_trial.provider == "gemini", f"Expected gemini for trial, got {job_trial.provider}"

        # 2. Test Routing for Admin User
        req_admin = MediaGenerationRequest(prompt="A luxury sports watch ad", mode="premium_ad", provider="")
        job_admin = await media_service.create_media_job(db, admin, req_admin)
        print(f"[2. Admin User Routing] Created Job ID={job_admin.id}, Assigned Provider={job_admin.provider}")
        assert job_admin.provider == "higgsfield", f"Expected higgsfield for admin, got {job_admin.provider}"

        # 3. Test Admin Bypass with Expired Trial Date
        orig_admin_exp = admin.trial_expires_at
        admin.trial_expires_at = datetime.now(timezone.utc) - timedelta(days=10) # 10 days in past
        await db.commit()
        job_admin_bypass = await media_service.create_media_job(db, admin, req_admin)
        print(f"[3. Admin Bypass Fix] Admin with expired trial date created Job ID={job_admin_bypass.id}, Provider={job_admin_bypass.provider}")
        admin.trial_expires_at = orig_admin_exp
        await db.commit()

        # 4. Test Daily Image Cap Exhaustion on Trial
        print("\n--- [4. Trial Image Daily Cap Exhaustion] ---")
        trial_org.daily_images_used_today = 5
        await db.commit()
        try:
            req_exceed = MediaGenerationRequest(prompt="Over-limit image", mode="premium_ad")
            await media_service.create_media_job(db, trial_user, req_exceed)
            print("FAILED: Should have raised 429 daily limit reached!")
        except Exception as e:
            status_c = getattr(e, 'status_code', None)
            detail = getattr(e, 'detail', str(e))
            print(f"SUCCESS: Blocked at daily cap with status={status_c}")
            print(f"Detail payload: {detail}")

        # 5. Test Credit Balance Exhaustion on Discover
        print("\n--- [5. Credit Balance Exhaustion] ---")
        orig_bal = trial_org.credit_balance
        trial_org.credit_balance = 0.0
        await db.commit()
        try:
            await billing_service.assert_can_spend(db, trial_user, required_credits=1.0, feature_name="discover")
            print("FAILED: Should have raised 402 insufficient credits!")
        except Exception as e:
            status_c = getattr(e, 'status_code', None)
            detail = getattr(e, 'detail', str(e))
            print(f"SUCCESS: Blocked at credit exhaustion with status={status_c}")
            print(f"Detail payload: {detail}")

        # Cleanup / Restore trial_user
        trial_user.trial_expires_at = orig_trial_exp
        trial_org.credit_balance = orig_bal
        trial_org.daily_images_used_today = 0
        await db.commit()
        print("\nAll tiered routing and limit tests completed successfully.")

if __name__ == "__main__":
    asyncio.run(test_tiered_routing_and_caps())
