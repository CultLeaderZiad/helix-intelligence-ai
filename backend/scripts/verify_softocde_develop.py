import asyncio
import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))

from app.db.session import async_session_maker
from app.models.user import User
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.creative import Creative
from app.models.usage_log import UsageLog
from app.services.discover_service import trigger_search
from app.schemas.discover import SearchParams
from sqlalchemy import select

async def verify_softocde_develop():
    print("=" * 60)
    print("VERIFYING ORIGINAL FAILING CASE: 'softocde develop'")
    print("=" * 60)

    async with async_session_maker() as db:
        user = (await db.execute(select(User).limit(1))).scalar_one()
        org = (await db.execute(select(Organization).where(Organization.owner_id == user.id))).scalar_one_or_none()
        if not org:
            org = (await db.execute(select(Organization).limit(1))).scalar_one()

        org.daily_credits_used_today = 0.0
        org.credit_balance = 50.0
        await db.commit()

        user_id = str(user.id)
        print(f"User: {user.email} (Org: {org.name})")

    params = SearchParams(query="softocde develop", country="US")
    async with async_session_maker() as db:
        job_schema = await trigger_search(db, params, user_id, background_tasks=None)
        job_id = job_schema.job_id if hasattr(job_schema, "job_id") else job_schema.id
        print(f"Triggered Job ID: {job_id}")

    print("Polling job completion...")
    for _ in range(35):
        await asyncio.sleep(2)
        async with async_session_maker() as db:
            job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one()
            print(f"  Status: {job.status} | Stage: {job.stage} | Label: {job.stage_label}")
            if job.status in ("succeeded", "failed"):
                break

    async with async_session_maker() as db:
        job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one()
        creatives = (await db.execute(select(Creative).where(Creative.job_id == job_id))).scalars().all()
        logs = (await db.execute(select(UsageLog).where(UsageLog.job_id == job_id))).scalars().all()

        print("\n" + "=" * 60)
        print("DATABASE EVIDENCE FOR 'softocde develop':")
        print("=" * 60)
        print(f"Job ID: {job.id}")
        print(f"Job Status: {job.status}")
        print(f"Job Stage: {job.stage}")
        print(f"Job Stage Label: {job.stage_label}")
        print(f"Job Record Count: {job.record_count}")
        print(f"Creatives Count in DB: {len(creatives)}")

        if len(creatives) > 0:
            print("WARNING: Found creatives for nonsense query:")
            for c in creatives:
                print(f"  - Headline: {c.headline}, Body: {c.body}")
        else:
            print("CONFIRMED: ZERO creatives created in database. Honest zero-results state verified.")

        print(f"\nDeduction History ({len(logs)} logs):")
        for l in logs:
            print(f"  - Provider: {l.provider}, Op: {l.operation}, Credits: {l.credits_deducted} cr, Cost: ${l.cost_usd}")

        # Assert no Bright Data was called or billed
        bd_logs = [l for l in logs if "brightdata" in (l.provider or "").lower() or "brightdata" in (l.operation or "").lower()]
        assert len(bd_logs) == 0, f"Bright Data was billed: {bd_logs}"
        assert len(creatives) == 0, f"Fabricated creatives found: {len(creatives)}"
        assert job.stage == "zero_results", f"Unexpected job stage: {job.stage}"

        print("\nALL ZERO-RESULTS ASSERTIONS PASSED WITH 100% HONEST EMPTY STATE.")

if __name__ == "__main__":
    asyncio.run(verify_softocde_develop())
