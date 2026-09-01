import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv("backend/.env")

from app.db.session import async_session_maker
from app.models.scrape_job import ScrapeJob
from app.models.creative import Creative
from app.models.creative_score import CreativeScore
from sqlalchemy import select

async def check():
    async with async_session_maker() as db:
        job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == "f8aad2f5-a19a-4afc-a035-4a1d1e632f7f"))).scalar_one_or_none()
        if job:
            print(f"Job ID: {job.id} | Status: {job.status} | Record Count: {job.record_count} | Stage: {job.stage_label}")

        creatives = (await db.execute(select(Creative).where(Creative.job_id == "f8aad2f5-a19a-4afc-a035-4a1d1e632f7f"))).scalars().all()
        print(f"\nCreatives Saved in Neon DB ({len(creatives)}):")
        for idx, c in enumerate(creatives):
            score = (await db.execute(select(CreativeScore).where(CreativeScore.creative_id == c.id))).scalar_one_or_none()
            score_val = score.composite if score else "—"
            print(f"  #{idx+1} [Format: {c.format}] Headline: '{c.headline}' | CTA: '{c.cta}' | Score: {score_val} | URL: {c.landing_url}")

if __name__ == "__main__":
    asyncio.run(check())
