import asyncio
import os
import sys
import datetime
import uuid

sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv("backend/.env")

from app.db.session import async_session_maker
from app.services import discover_service, creative_service, billing_service
from app.services.ai.ai_router import AIRouter
from app.schemas.discover import SearchParams
from app.models.user import User
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.creative import Creative
from sqlalchemy import select

async def main():
    print("=" * 70)
    print("TEST 1: ADMIN WITH PAST TRIAL_EXPIRES_AT (SHOULD NEVER BE BLOCKED)")
    print("=" * 70)

    now = datetime.datetime.now(datetime.timezone.utc)
    past_date = now - datetime.timedelta(days=30)

    async with async_session_maker() as db:
        # Create/find Admin with past trial date
        admin_id = f"admin_expired_trial_{uuid.uuid4().hex[:6]}"
        admin_user = User(
            id=admin_id,
            email=f"{admin_id}@helix.io",
            password_hash="hash",
            role="admin",
            trial_expires_at=past_date
        )
        db.add(admin_user)
        await db.commit()

        admin_org = Organization(
            id=f"org_{admin_id}",
            name="Admin Expired Trial Org",
            owner_id=admin_user.id,
            plan_id="plan_trial_default",
            credit_balance=50.0
        )
        db.add(admin_org)
        await db.commit()

        # 1. Test is_trial_active helper
        is_active = billing_service.is_trial_active(admin_user)
        days_rem = billing_service.get_trial_days_remaining(admin_user)
        print(f"Admin is_trial_active: {is_active} (Expected: True)")
        print(f"Admin get_trial_days_remaining: {days_rem} (Expected: 999)")

        # 2. Test AIRouter
        ai_provider = await AIRouter.get_provider_for_user(db, admin_user)
        print(f"Admin AIRouter Provider returned: {type(ai_provider).__name__} (Expected: MultiTierAIProvider)")

        # 3. Test assert_can_spend
        org_out, plan_out = await billing_service.assert_can_spend(db, admin_user, 1.0, "discover")
        print(f"Admin assert_can_spend returned plan: {plan_out.name} (Expected: Helix Administrator)")

        print("\n" + "=" * 70)
        print("TEST 2: NON-ADMIN EXPIRED TRIAL (GRACEFUL DEGRADATION IN DISCOVER)")
        print("=" * 70)

        cust_id = f"cust_expired_{uuid.uuid4().hex[:6]}"
        cust_user = User(
            id=cust_id,
            email=f"{cust_id}@helix.io",
            password_hash="hash",
            role="customer",
            trial_expires_at=past_date
        )
        db.add(cust_user)
        await db.commit()

        cust_org = Organization(
            id=f"org_{cust_id}",
            name="Customer Expired Org",
            owner_id=cust_user.id,
            plan_id="plan_trial_default",
            credit_balance=50.0
        )
        db.add(cust_org)
        await db.commit()

        # Create a ScrapeJob simulating real scraping completed
        job_id = str(uuid.uuid4())
        job = ScrapeJob(
            id=job_id,
            org_id=cust_org.id,
            query="allbirds",
            status="running",
            created_at=now,
            stage="scraping",
            stage_label="Scraping Platforms",
            progress=0.2,
            stage_index=1,
            record_count=0
        )
        db.add(job)
        await db.commit()

        print(f"Created Scrape Job {job_id} for expired trial user {cust_user.email}")
        print("Running discovery pipeline (Scraping -> Saving -> AI Scoring graceful skip)...")
        await discover_service.run_discovery_pipeline(job_id, "allbirds", {})

        # Check job completion
        async with async_session_maker() as verify_db:
            final_job = (await verify_db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one()
            print(f"Final Job Status: '{final_job.status}' (Expected: 'succeeded')")
            print(f"Final Job Stage: '{final_job.stage}' | Stage Label: '{final_job.stage_label}'")
            print(f"Final Job Records Found: {final_job.record_count} (Expected: > 0)")

            creatives_in_db = (await verify_db.execute(select(Creative).where(Creative.job_id == job_id))).scalars().all()
            print(f"Total Creatives Saved in DB: {len(creatives_in_db)}")
            if creatives_in_db:
                safe_headline = str(creatives_in_db[0].headline).encode("ascii", "replace").decode("ascii")
                print(f"  Sample Saved Creative: Headline='{safe_headline}', Format={creatives_in_db[0].format}")

        print("\n" + "=" * 70)
        print("TEST 3: PRE-FLIGHT BLOCK FOR EXPIRED TRIAL & ZERO CREDITS")
        print("=" * 70)

        # Confirm assert_can_spend still correctly blocks expired non-admin users at initiation
        try:
            await billing_service.assert_can_spend(db, cust_user, 1.0, "discover")
            print("Pre-flight Check: UNEXPECTED PASS")
        except Exception as e:
            err_text = str(e).encode("ascii", "replace").decode("ascii")
            print(f"Pre-flight Check: Correctly Blocked with: {err_text}")

if __name__ == "__main__":
    asyncio.run(main())
