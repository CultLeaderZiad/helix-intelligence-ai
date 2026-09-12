"""Inspect creatives without assuming brand_name."""
import os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from app.db.session import async_session_maker


async def main():
    async with async_session_maker() as db:
        cols = (
            await db.execute(
                text(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'creatives' ORDER BY ordinal_position
                    """
                )
            )
        ).scalars().all()
        print("creative_columns", cols)

        nike = (
            await db.execute(
                text(
                    "SELECT count(*) FROM creatives WHERE headline ILIKE '%Nike%' OR body ILIKE '%Nike%'"
                )
            )
        ).scalar()
        madrid = (
            await db.execute(
                text(
                    "SELECT count(*) FROM creatives WHERE headline ILIKE '%madrid%' OR body ILIKE '%madrid%'"
                )
            )
        ).scalar()
        print("creatives_mentioning_nike", nike)
        print("creatives_mentioning_madrid", madrid)

        sample = (
            await db.execute(
                text(
                    """
                    SELECT left(c.headline, 90) AS headline, c.landing_domain, c.data_source, j.query, j.record_count
                    FROM creatives c
                    LEFT JOIN scrape_jobs j ON j.id = c.job_id
                    ORDER BY c.created_at DESC
                    LIMIT 10
                    """
                )
            )
        ).mappings().all()
        print("latest_creatives")
        for r in sample:
            print(" ", r["query"], "n=", r["record_count"], "|", r["headline"], "|", r["landing_domain"], r["data_source"])

        gym = (
            await db.execute(
                text(
                    """
                    SELECT left(headline, 90) AS headline, landing_domain
                    FROM creatives
                    WHERE job_id IN (SELECT id FROM scrape_jobs WHERE query ILIKE 'gymshark')
                    LIMIT 5
                    """
                )
            )
        ).mappings().all()
        print("gymshark_samples")
        for r in gym:
            print(" ", r["headline"], r["landing_domain"])


asyncio.run(main())
