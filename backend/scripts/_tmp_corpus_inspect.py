"""Inspect recent creatives/jobs. No secrets."""
import os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from app.db.session import async_session_maker


async def main():
    async with async_session_maker() as db:
        jobs = (
            await db.execute(
                text(
                    """
                    SELECT id, query, status, stage, left(coalesce(stage_label,''), 140) AS label,
                           record_count, created_at
                    FROM scrape_jobs
                    ORDER BY created_at DESC
                    LIMIT 12
                    """
                )
            )
        ).mappings().all()
        print("latest_jobs")
        for j in jobs:
            print(" ", j["created_at"], j["status"], j["record_count"], j["query"], "|", j["label"])

        nike = (
            await db.execute(
                text(
                    """
                    SELECT count(*) AS n FROM creatives
                    WHERE headline ILIKE '%Nike Running%' OR body ILIKE '%Nike Running%'
                    """
                )
            )
        ).scalar()
        madrid = (
            await db.execute(
                text(
                    """
                    SELECT count(*) AS n FROM creatives
                    WHERE headline ILIKE '%madrid%' OR body ILIKE '%madrid%' OR brand_name ILIKE '%madrid%'
                    """
                )
            )
        ).scalar()
        print("creatives_nike_running", nike)
        print("creatives_madrid", madrid)

        sample = (
            await db.execute(
                text(
                    """
                    SELECT left(c.headline, 80) AS headline, c.brand_name, c.landing_domain, c.data_source, j.query
                    FROM creatives c
                    LEFT JOIN scrape_jobs j ON j.id = c.job_id
                    ORDER BY c.created_at DESC
                    LIMIT 8
                    """
                )
            )
        ).mappings().all()
        print("latest_creatives")
        for r in sample:
            print(" ", r["query"], "|", r["brand_name"], "|", r["headline"], "|", r["data_source"], r["landing_domain"])


asyncio.run(main())
