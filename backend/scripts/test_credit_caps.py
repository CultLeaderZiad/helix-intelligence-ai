import asyncio
import sys
import os
import uuid
import datetime
from fastapi import HTTPException
from sqlalchemy import select

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import async_session_maker
from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.scrape_job import ScrapeJob
from app.models.creative import Creative
from app.schemas.discover import SearchParams
from app.schemas.media import MediaGenerationRequest
from app.services.billing_service import (
    assert_can_spend,
    charge,
    refund,
    get_or_create_default_org,
    DISCOVER_SEARCH_CREDIT_COST,
    CREATE_IMAGE_CREDIT_COST,
    CREATE_VIDEO_CREDIT_COST,
    ANALYSIS_PATTERN_CREDIT_COST,
)
from app.services import discover_service, media_service, analysis_service

async def run_credit_cap_tests():
    print("=" * 60, flush=True)
    print("HELIX CREDIT CAPS & PROVIDER CHAIN TEST SUITE", flush=True)
    print("=" * 60, flush=True)

    async with async_session_maker() as db:
        # Create a unique test user
        test_email = f"test_credits_{uuid.uuid4().hex[:8]}@example.com"
        test_user = User(
            id=str(uuid.uuid4()),
            email=test_email,
            password_hash="fake_hashed_pw",
            role="customer",
            trial_expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7),
            has_completed_onboarding=True
        )
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)
        print(f"[+] Created test user: {test_user.email} (id: {test_user.id})", flush=True)

        # 1. Test get_or_create_default_org creates trial org with 25 credits
        org = await get_or_create_default_org(db, test_user, lock_row=True)
        assert org.credit_balance == 25.0, f"Expected 25.0 initial credits, got {org.credit_balance}"
        print(f"[PASS] Default trial org initialized with balance: {org.credit_balance} credits", flush=True)

        # 2. Test assert_can_spend passes for Discover (2.0 credits)
        org, plan = await assert_can_spend(db, test_user, required_credits=DISCOVER_SEARCH_CREDIT_COST, feature_name="discover")
        print(f"[PASS] assert_can_spend approved for Discover ({DISCOVER_SEARCH_CREDIT_COST} credits)", flush=True)

        # 3. Test Discover trigger_search deducts 2.0 credits
        params = SearchParams(query=f"Nike Running {uuid.uuid4().hex[:4]}")
        job = await discover_service.trigger_search(db, params, test_user.id)
        await db.refresh(org)
        assert org.credit_balance == 23.0, f"Expected 23.0 credits after Discover, got {org.credit_balance}"
        assert org.daily_credits_used_today == 2.0, f"Expected 2.0 daily used, got {org.daily_credits_used_today}"
        print(f"[PASS] trigger_search deducted {DISCOVER_SEARCH_CREDIT_COST} credits. New balance: {org.credit_balance}", flush=True)

        # 4. Test 12-Hour Query Deduplication Cache (Should return cached job, 0 credits charged)
        job_db = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job.job_id))).scalar_one()
        job_db.status = "succeeded"
        await db.commit()

        cached_job = await discover_service.trigger_search(db, params, test_user.id)
        assert cached_job.job_id == job.job_id, "Expected cached job_id to match"
        await db.refresh(org)
        assert org.credit_balance == 23.0, f"Expected 23.0 credits (no deduction for cache hit), got {org.credit_balance}"
        print(f"[PASS] 12h Cache Hit verified. Job returned from cache with 0 credit deduction.", flush=True)

        # Reset daily usage for next tests
        org.daily_credits_used_today = 0.0
        await db.commit()

        # 5. Test Media Generation Gating (Image: 3.0 credits)
        media_req = MediaGenerationRequest(
            prompt="A futuristic neon shoe",
            provider="pollinations",
            mode="quick_concept" # image mode -> 3.0 credits <= 3.5 daily limit
        )
        media_job = await media_service.create_media_job(db, test_user, media_req)
        await db.refresh(org)
        assert org.credit_balance == 20.0, f"Expected 20.0 credits after Image gen, got {org.credit_balance}"
        print(f"[PASS] Media image job created. Deducted {CREATE_IMAGE_CREDIT_COST} credits. Balance: {org.credit_balance}", flush=True)

        # 6. Test Video Generation Gating with Pro Plan (8.0 credits, daily_limit=None)
        pro_plan_id = f"plan_pro_{uuid.uuid4().hex[:6]}"
        pro_plan = Plan(
            id=pro_plan_id,
            name="Pro Growth Plan",
            type="pay_as_you_go",
            credit_allowance=500,
            daily_credit_limit=None,
            feature_flags={"discover": True, "intelligence": True, "create": True, "performance": True, "swipe_files": True}
        )
        db.add(pro_plan)
        org.plan_id = pro_plan_id
        org.credit_balance = 100.0
        await db.commit()

        video_req = MediaGenerationRequest(
            prompt="A shoe transforming into light",
            provider="pollinations",
            mode="quick_video" # video mode -> 8.0 credits
        )
        video_job = await media_service.create_media_job(db, test_user, video_req)
        await db.refresh(org)
        assert org.credit_balance == 92.0, f"Expected 92.0 credits after Video gen, got {org.credit_balance}"
        print(f"[PASS] Media video job created (Pro Plan). Deducted {CREATE_VIDEO_CREDIT_COST} credits. Balance: {org.credit_balance}", flush=True)

        # 7. Test Insufficient Credits (402 Payment Required)
        org.credit_balance = 1.0
        await db.commit()
        
        try:
            await assert_can_spend(db, test_user, required_credits=8.0, feature_name="create")
            assert False, "Should have raised 402 HTTPException"
        except HTTPException as e:
            assert e.status_code == 402, f"Expected 402, got {e.status_code}"
            assert e.detail.get("code") == "insufficient_credits", f"Expected code insufficient_credits, got {e.detail}"
            print(f"[PASS] Insufficient credits blocked with HTTP 402: {e.detail}", flush=True)

        # 8. Test Daily Limit Reached (429 Too Many Requests)
        # Switch back to trial plan with 3.5 daily limit
        org.plan_id = "plan_trial_default"
        org.credit_balance = 50.0
        org.daily_credits_used_today = 3.5
        await db.commit()

        try:
            await assert_can_spend(db, test_user, required_credits=2.0, feature_name="discover")
            assert False, "Should have raised 429 HTTPException"
        except HTTPException as e:
            assert e.status_code == 429, f"Expected 429, got {e.status_code}"
            assert e.detail.get("code") == "daily_limit_reached", f"Expected code daily_limit_reached, got {e.detail}"
            print(f"[PASS] Daily limit blocked with HTTP 429: {e.detail}", flush=True)

        # 9. Test Admin Bypass (Admin role has no credit block)
        admin_user = User(
            id=str(uuid.uuid4()),
            email=f"admin_{uuid.uuid4().hex[:6]}@helix.com",
            password_hash="fake_hashed_pw",
            role="admin",
            trial_expires_at=None
        )
        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)

        admin_org, admin_plan = await assert_can_spend(db, admin_user, required_credits=9999.0, feature_name="discover")
        assert admin_plan.type == "admin", "Expected admin plan"
        print(f"[PASS] Administrator successfully bypassed credit caps and feature flags.", flush=True)

        # 10. Clean up test records
        from sqlalchemy import delete
        from app.models.usage_log import UsageLog
        from app.models.media_job import MediaGenerationJob
        await db.execute(delete(UsageLog).where(UsageLog.user_id.in_([test_user.id, admin_user.id])))
        await db.execute(delete(MediaGenerationJob).where(MediaGenerationJob.user_id == test_user.id))
        await db.execute(delete(ScrapeJob).where(ScrapeJob.org_id == org.id))
        await db.execute(delete(Organization).where(Organization.owner_id.in_([test_user.id, admin_user.id])))
        await db.execute(delete(Plan).where(Plan.id == pro_plan_id))
        await db.execute(delete(User).where(User.id.in_([test_user.id, admin_user.id])))
        await db.commit()
        print("[+] Test cleanup completed successfully.", flush=True)

    print("=" * 60, flush=True)
    print("ALL TESTS PASSED SUCCESSFULLY (10/10)", flush=True)
    print("=" * 60, flush=True)

if __name__ == "__main__":
    asyncio.run(run_credit_cap_tests())
