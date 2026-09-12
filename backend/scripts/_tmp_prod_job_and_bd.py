"""Recent Discover jobs + a Bright Data key ping. No secrets printed."""
import os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from sqlalchemy import text
from app.core.config import settings
from app.db.session import async_session_maker


async def main():
    async with async_session_maker() as db:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT id, query, status, stage, stage_label, error_msg, record_count, created_at
                    FROM scrape_jobs
                    WHERE query ILIKE :q
                    ORDER BY created_at DESC
                    LIMIT 5
                    """
                ),
                {"q": "%real madrid%"},
            )
        ).mappings().all()
        print("recent_real_madrid_jobs", len(rows))
        for r in rows:
            print(
                " ",
                r["status"],
                r["stage"],
                "records=",
                r["record_count"],
                "label=",
                (r["stage_label"] or "")[:160],
                "err=",
                (r["error_msg"] or "")[:120],
            )

    key = (settings.BRIGHTDATA_API_KEY or "").strip().strip("\"'")
    headers = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        for url in (
            "https://api.brightdata.com/customer/balance",
            "https://api.brightdata.com/zone",
            "https://api.brightdata.com/datasets/v3/list",
        ):
            r = await client.get(url, headers=headers)
            print("BRIGHTDATA", url.split(".com")[-1], "status=", r.status_code, "body=", (r.text or "")[:140])


asyncio.run(main())
