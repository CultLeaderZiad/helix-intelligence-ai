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
from app.models.creative_score import CreativeScore
from app.models.usage_log import UsageLog
from app.models.pattern import Pattern
from app.services.discover_service import trigger_search
from app.schemas.discover import SearchParams
from sqlalchemy import select, desc

async def run_verification():
    async with async_session_maker() as db:
        user = (await db.execute(select(User).limit(1))).scalar_one()
        org = (await db.execute(select(Organization).where(Organization.owner_id == user.id))).scalar_one_or_none()
        if not org:
            org = (await db.execute(select(Organization).limit(1))).scalar_one()

        user_id = str(user.id)
        print(f"Running verification with User: {user.email} (Org: {org.name}, ID: {org.id})")
        print(f"Starting Credit Balance: {org.credit_balance}")

    test_queries = [
        ("shopify", "Real Brand 1"),
        ("gymshark", "Real Brand 2"),
        ("nike", "Real Brand 3"),
        ("softocde develop", "Nonsense / Nonexistent Brand")
    ]

    results_summary = []

    for query_str, description in test_queries:
        print(f"\n==========================================")
        print(f"TESTING: '{query_str}' ({description})")
        print(f"==========================================")

        async with async_session_maker() as db:
            org = (await db.execute(select(Organization).where(Organization.id == org.id))).scalar_one()
            org.daily_credits_used_today = 0.0
            org.credit_balance = 50.0
            await db.commit()

        async with async_session_maker() as db:
            params = SearchParams(query=query_str, country="US")
            job_schema = await trigger_search(db, params, user_id, background_tasks=None)
            job_id = job_schema.job_id if hasattr(job_schema, "job_id") else job_schema.id
            print(f"Triggered Job ID: {job_id}")

        # Wait for the background pipeline to finish
        for _ in range(45):
            await asyncio.sleep(2)
            async with async_session_maker() as db:
                job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one()
                print(f"  Job Status: {job.status} | Stage: {job.stage} | Label: {job.stage_label} | Elapsed: {job.elapsed_ms}ms")
                if job.status in ("succeeded", "failed"):
                    break

        async with async_session_maker() as db:
            job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one()
            creatives = (await db.execute(
                select(Creative, CreativeScore)
                .outerjoin(CreativeScore, Creative.id == CreativeScore.creative_id)
                .where(Creative.job_id == job_id)
            )).all()

            logs = (await db.execute(
                select(UsageLog).where(UsageLog.job_id == job_id).order_by(UsageLog.created_at.asc())
            )).scalars().all()

            patterns = (await db.execute(
                select(Pattern).where(Pattern.job_id == job_id)
            )).scalars().all()

            print(f"\n--- FINAL RESULTS FOR '{query_str}' ---")
            print(f"Job Status: {job.status}")
            print(f"Job Stage: {job.stage}")
            print(f"Job Stage Label: {job.stage_label}")
            print(f"Record Count in Job: {job.record_count}")
            print(f"Creatives in DB: {len(creatives)}")

            for idx, (c, score) in enumerate(creatives[:2]):
                print(f"  Creative #{idx+1}:")
                print(f"    Platform: {c.platform}, Format: {c.format}")
                print(f"    Headline: {repr(c.headline)}")
                print(f"    Body: {repr(c.body[:100] if c.body else '')}")
                print(f"    CTA: {repr(c.cta)}")
                print(f"    Landing Domain: {repr(c.landing_domain)}")
                print(f"    Data Source: {c.data_source}")
                print(f"    Score Hook: {score.hook if score else None}, Clarity: {score.clarity if score else None}, Composite: {score.composite if score else None}")

            print(f"\nUsage / Deductions ({len(logs)} logs):")
            for l in logs:
                print(f"  Provider: {l.provider}, Op: {l.operation}, Deducted: {l.credits_deducted} cr, Cost: ${l.cost_usd}")

            results_summary.append({
                "query": query_str,
                "description": description,
                "status": job.status,
                "stage": job.stage,
                "stage_label": job.stage_label,
                "records_count": len(creatives),
                "providers_billed": [l.provider for l in logs],
                "credits_billed": sum(l.credits_deducted for l in logs),
                "sample_headline": creatives[0][0].headline if creatives else None,
                "sample_body": creatives[0][0].body if creatives else None,
            })

    print("\n==========================================")
    print("FINAL VERIFICATION SUMMARY")
    print("==========================================")
    print(json.dumps(results_summary, indent=2))

if __name__ == "__main__":
    asyncio.run(run_verification())
