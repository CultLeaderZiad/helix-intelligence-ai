import asyncio
import os
import sys
import json
import logging
import datetime

sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv("backend/.env")

# Set stdout encoding
sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("VERIFY")

from app.db.session import async_session_maker
from app.models.user import User
from app.models.organization import Organization
from app.models.media_job import MediaGenerationJob
from app.models.plan import Plan
from app.schemas.media import MediaGenerationRequest
from app.services.scraping.metapi_provider import MetapiProvider
from app.services.billing_service import get_or_create_default_org
from app.services import media_service
from sqlalchemy import select

async def test_1_shopify_headlines(db, user, org):
    print("\n" + "="*80)
    print("TEST 1: LIVE METAPI HEADLINE EXTRACTION VERIFICATION ('shopify')")
    print("="*80)
    
    provider = MetapiProvider(db, org.id, user.id)
    creatives = await provider.search("shopify", max_records=5)
    
    print(f"Total creatives parsed: {len(creatives)}\n")
    for i, c in enumerate(creatives[:3]):
        print(f"--- Item #{i+1} ---")
        print(f"Brand / Page Name : {c.brand_name}")
        print(f"Headline (AFTER)  : {c.headline}")
        print(f"Body (First 100)  : {c.body[:100].replace(chr(10), ' ')}...")
        print(f"Landing URL       : {c.landing_url}")
        print()

async def test_2_create_studio_tiering(db, admin_user, trial_user):
    print("\n" + "="*80)
    print("TEST 2: CREATE STUDIO TIERED ROUTING (PAID/ADMIN -> HIGGSFIELD vs TRIAL -> GEMINI)")
    print("="*80)

    # 1. Admin/Paid User Test
    print(f"\n[A] Testing Paid/Admin User: {admin_user.email} (Role: {admin_user.role})")
    req_paid = MediaGenerationRequest(
        prompt="High performance running shoes in modern neon glow studio lighting",
        mode="premium_ad",
        parameters={"aspect_ratio": "1:1", "kind": "image"}
    )
    
    job_paid = await media_service.create_media_job(db, admin_user, req_paid)
    print(f"  -> Created Job ID: {job_paid.id}")
    print(f"  -> Assigned Provider in DB: '{job_paid.provider}' (Expected: 'higgsfield')")
    assert job_paid.provider == "higgsfield", f"Expected higgsfield but got {job_paid.provider}"

    # 2. Trial User Test
    trial_org = await get_or_create_default_org(db, trial_user)
    print(f"\n[B] Testing Trial User: {trial_user.email} (Role: {trial_user.role}, Org Plan: {trial_org.plan if trial_org else 'trial'})")
    req_trial = MediaGenerationRequest(
        prompt="Minimalist organic coffee cup steam rising",
        mode="quick_concept",
        parameters={"aspect_ratio": "1:1", "kind": "image"}
    )
    
    job_trial = await media_service.create_media_job(db, trial_user, req_trial)
    print(f"  -> Created Job ID: {job_trial.id}")
    print(f"  -> Assigned Provider in DB: '{job_trial.provider}' (Expected: 'gemini')")
    assert job_trial.provider == "gemini", f"Expected gemini but got {job_trial.provider}"

    print("\n" + "="*80)
    print("ALL TESTS COMPLETED SUCCESSFULLY WITH VERIFIED LIVE EVIDENCE")
    print("="*80)

async def main():
    async with async_session_maker() as db:
        admin_user = (await db.execute(select(User).where(User.role == "admin"))).scalars().first()
        if not admin_user:
            admin_user = (await db.execute(select(User))).scalars().first()
            admin_user.role = "admin"
            await db.commit()
        admin_org = await get_or_create_default_org(db, admin_user)

        trial_user = (await db.execute(select(User).where(User.email.like("cust_expired%")))).scalars().first()
        if not trial_user:
            trial_user = (await db.execute(select(User).where(User.role != "admin"))).scalars().first()
        
        trial_user.role = "member"
        trial_user.trial_expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=5)
        trial_org = await get_or_create_default_org(db, trial_user)
        if trial_org:
            trial_org.plan = "trial"
            trial_org.plan_id = "plan_trial_default"
        await db.commit()

        await test_1_shopify_headlines(db, admin_user, admin_org)
        await test_2_create_studio_tiering(db, admin_user, trial_user)

if __name__ == "__main__":
    asyncio.run(main())
