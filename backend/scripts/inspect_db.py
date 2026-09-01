import asyncio
import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))

from app.db.session import async_session_maker
from app.models.scrape_job import ScrapeJob
from app.models.creative import Creative
from app.models.creative_score import CreativeScore
from app.models.usage_log import UsageLog
from app.models.pattern import Pattern
from sqlalchemy import select, desc

async def inspect():
    async with async_session_maker() as db:
        print("=== RECENT SCRAPE JOBS ===")
        jobs = await db.execute(select(ScrapeJob).order_by(desc(ScrapeJob.created_at)).limit(5))
        for j in jobs.scalars().all():
            print(f"Job ID: {j.id}, Query: '{j.query}', Status: {j.status}, Stage: {j.stage}, Label: '{j.stage_label}', Records: {j.record_count}, Elapsed: {j.elapsed_ms}ms, Created: {j.created_at}")

        print("\n=== RECENT USAGE LOGS ===")
        logs = await db.execute(select(UsageLog).order_by(desc(UsageLog.created_at)).limit(10))
        for l in logs.scalars().all():
            print(f"Log ID: {l.id}, JobID: {l.job_id}, Op: {l.operation}, Provider: {l.provider}, Deducted: {l.credits_deducted}, CostUSD: {l.cost_usd}, Meta: {l.metadata_json}, Created: {l.created_at}")

        print("\n=== RECENT CREATIVES ===")
        creatives = await db.execute(select(Creative, CreativeScore).outerjoin(CreativeScore, Creative.id == CreativeScore.creative_id).order_by(desc(Creative.id)).limit(5))
        for c, score in creatives.all():
            print(f"Creative ID: {c.id}")
            print(f"  Job ID: {c.job_id}")
            print(f"  Brand ID / Platform: {c.brand_id} / {c.platform}")
            print(f"  Headline: {c.headline}")
            print(f"  Body: {c.body}")
            print(f"  CTA: {c.cta}")
            print(f"  Landing: {c.landing_domain}")
            print(f"  Data Source: {c.data_source}, Is Estimated: {c.is_estimated}")
            print(f"  Impressions: {c.impressions_est}, Spend: {c.spend_band}")
            if score:
                print(f"  Scores -> Hook: {score.hook}, Clarity: {score.clarity}, Retention: {score.retention}, Composite: {score.composite}")
            else:
                print("  Scores -> None")
                
        print("\n=== RECENT PATTERNS ===")
        patterns = await db.execute(select(Pattern).order_by(desc(Pattern.id)).limit(10))
        for p in patterns.scalars().all():
            print(f"Pattern ID: {p.id}, JobID: {p.job_id}, Label: {p.label}, Family: {p.family}, Prevalence: {p.prevalence}, Lift: {p.lift_index}")

if __name__ == "__main__":
    asyncio.run(inspect())
