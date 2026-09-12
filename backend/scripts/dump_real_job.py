import asyncio
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv("backend/.env")

from app.db.session import async_session_maker
from app.models.scrape_job import ScrapeJob
from app.models.creative import Creative
from app.models.creative_score import CreativeScore
from app.models.usage_log import UsageLog
from app.models.pattern import Pattern
from app.models.organization import Organization
from sqlalchemy import select

def serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)

async def dump_job(job_id: str):
    async with async_session_maker() as db:
        job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one_or_none()
        if not job:
            print(f"Job {job_id} not found")
            return

        org = (await db.execute(select(Organization).where(Organization.id == job.org_id))).scalar_one_or_none()
        logs = (await db.execute(select(UsageLog).where(UsageLog.job_id == job_id))).scalars().all()
        creatives = (await db.execute(select(Creative).where(Creative.job_id == job_id))).scalars().all()
        
        scores_list = []
        for c in creatives:
            score = (await db.execute(select(CreativeScore).where(CreativeScore.creative_id == c.id))).scalar_one_or_none()
            if score:
                scores_list.append({
                    "creative_id": score.creative_id,
                    "hook": score.hook,
                    "clarity": score.clarity,
                    "retention": score.retention,
                    "composite": score.composite
                })

        patterns = (await db.execute(select(Pattern).where(Pattern.job_id == job_id))).scalars().all()

        output = {
            "scrape_job": {
                "id": job.id,
                "org_id": job.org_id,
                "query": job.query,
                "status": job.status,
                "stage": job.stage,
                "stage_label": job.stage_label,
                "stage_index": job.stage_index,
                "stages_total": job.stages_total,
                "progress": job.progress,
                "record_count": job.record_count,
                "elapsed_ms": job.elapsed_ms,
                "created_at": serialize(job.created_at),
                "completed_at": serialize(job.completed_at),
                "error_msg": job.error_msg
            },
            "organization": {
                "id": org.id,
                "plan": org.plan,
                "plan_id": org.plan_id,
                "credit_balance": org.credit_balance,
                "credits_used": org.credits_used,
                "daily_credits_used_today": org.daily_credits_used_today
            } if org else None,
            "usage_logs": [
                {
                    "id": l.id,
                    "org_id": l.org_id,
                    "job_id": l.job_id,
                    "provider": l.provider,
                    "operation": l.operation,
                    "units": l.units,
                    "cost_usd": l.cost_usd,
                    "credits_deducted": l.credits_deducted,
                    "metadata": l.metadata_json,
                    "created_at": serialize(l.created_at)
                } for l in logs
            ],
            "creatives_count": len(creatives),
            "creatives_sample": [
                {
                    "id": c.id,
                    "platform": c.platform,
                    "format": c.format,
                    "headline": c.headline,
                    "body_snippet": c.body[:120] if c.body else "",
                    "cta": c.cta,
                    "landing_domain": c.landing_domain,
                    "data_source": c.data_source,
                    "is_estimated": c.is_estimated,
                    "impressions_est": c.impressions_est,
                    "spend_band": c.spend_band,
                    "duration_seconds": c.duration_seconds
                } for c in creatives[:3]
            ],
            "scores_sample": scores_list[:3],
            "patterns": [
                {
                    "id": p.id,
                    "label": p.label,
                    "family": p.family,
                    "prevalence": p.prevalence,
                    "lift_index": p.lift_index
                } for p in patterns
            ]
        }

        with open("backend/scripts/job_dump.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print("Successfully dumped job to backend/scripts/job_dump.json")

if __name__ == "__main__":
    job_id = sys.argv[1] if len(sys.argv) > 1 else "1ed320f0-9daf-4b43-b32a-44bd5ecf0f90"
    asyncio.run(dump_job(job_id))
