import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))

from app.db.session import async_session_maker
from app.models.scrape_job import ScrapeJob
from app.models.creative import Creative
from app.models.creative_score import CreativeScore
from app.models.usage_log import UsageLog
from app.models.pattern import Pattern
from sqlalchemy import select

async def inspect_job(job_id: str):
    async with async_session_maker() as db:
        print(f"=== DETAILS FOR JOB {job_id} ===")
        job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one_or_none()
        if job:
            print(f"Job: ID={job.id}, Query='{job.query}', Status={job.status}, Stage={job.stage}, Label='{job.stage_label}', Records={job.record_count}, Elapsed={job.elapsed_ms}ms, Created={job.created_at}")

        print("\n--- USAGE LOGS ---")
        logs = (await db.execute(select(UsageLog).where(UsageLog.job_id == job_id))).scalars().all()
        for l in logs:
            print(f"  Log ID: {l.id}, Provider: {l.provider}, Op: {l.operation}, Deducted: {l.credits_deducted}, CostUSD: {l.cost_usd}, Meta: {l.metadata_json}, Created: {l.created_at}")

        print("\n--- CREATIVES ---")
        creatives = (await db.execute(select(Creative, CreativeScore).outerjoin(CreativeScore, Creative.id == CreativeScore.creative_id).where(Creative.job_id == job_id))).all()
        for c, score in creatives:
            print(f"  Creative ID: {c.id}")
            print(f"    Platform / Format: {c.platform} / {c.format}")
            print(f"    Headline: {c.headline}")
            print(f"    Body: {c.body}")
            print(f"    CTA: {c.cta}")
            print(f"    Landing: {c.landing_domain}")
            print(f"    Data Source: {c.data_source}, Is Estimated: {c.is_estimated}")
            print(f"    Impressions: {c.impressions_est}, Spend: {c.spend_band}")
            if score:
                print(f"    Scores -> Hook: {score.hook}, Clarity: {score.clarity}, Retention: {score.retention}, Composite: {score.composite}")
            else:
                print("    Scores -> None")

        print("\n--- PATTERNS ---")
        patterns = (await db.execute(select(Pattern).where(Pattern.job_id == job_id))).scalars().all()
        for p in patterns:
            print(f"  Pattern: ID={p.id}, Label={repr(p.label)}, Family={p.family}, Prevalence={p.prevalence}, Lift={p.lift_index}")

async def main():
    for jid in ["56753a03-7326-49c2-bc20-341a8f0a0b02", "6f0b945c-7ac8-4ca1-8c5d-d390990684e7"]:
        await inspect_job(jid)
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
