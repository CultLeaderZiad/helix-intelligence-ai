from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from sqlalchemy import select
from fastapi import HTTPException, BackgroundTasks
from app.schemas.discover import SearchParams, Job
from app.schemas.common import Paginated
from app.models.scrape_job import ScrapeJob
from app.models.organization import Organization
from app.core.config import settings
from app.db.session import async_session_maker
import datetime
import asyncio

async def trigger_search(db: AsyncSession, search_params: SearchParams, user_id: str, background_tasks: Optional[BackgroundTasks] = None) -> Job:
    if settings.USE_MOCKS:
        return Job(
            job_id="mock-job-id-123",
            status="running",
            progress=0.1,
            stage="init",
            stage_label="Initializing Search",
            stage_index=0,
            stages_total=5,
            records_found=0,
            elapsed_ms=100,
            created_at=datetime.datetime.utcnow().isoformat() + "Z"
        )
    
    # Get first org for user for now (or mock org if none)
    result = await db.execute(select(Organization).where(Organization.owner_id == user_id))
    org = result.scalar_one_or_none()
    
    org_id = org.id if org else "mock-org-id"
    
    new_job = ScrapeJob(
        org_id=org_id,
        query=search_params.query,
        status="running",
        created_at=datetime.datetime.utcnow(),
        progress=0.1,
        stage="init",
        stage_label="Initializing Search",
        stage_index=0,
        stages_total=5,
        elapsed_ms=100,
        record_count=0
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    if background_tasks:
        background_tasks.add_task(run_scrape_simulation, new_job.id, search_params.query)

    return Job(
        job_id=new_job.id,
        status=new_job.status,
        progress=new_job.progress,
        stage=new_job.stage,
        stage_label=new_job.stage_label,
        stage_index=new_job.stage_index,
        stages_total=new_job.stages_total,
        records_found=new_job.record_count,
        elapsed_ms=new_job.elapsed_ms,
        created_at=new_job.created_at.isoformat() + "Z" if new_job.created_at else ""
    )

async def get_job_status(db: AsyncSession, job_id: str) -> Job:
    if settings.USE_MOCKS:
        return Job(
            job_id=job_id,
            status="running",
            progress=0.5,
            stage="scraping",
            stage_label="Scraping Platforms",
            stage_index=2,
            stages_total=5,
            records_found=15,
            elapsed_ms=5000,
            created_at=datetime.datetime.utcnow().isoformat() + "Z"
        )
    
    result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return Job(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        stage=job.stage,
        stage_label=job.stage_label,
        stage_index=job.stage_index,
        stages_total=job.stages_total,
        records_found=job.record_count,
        elapsed_ms=job.elapsed_ms,
        created_at=job.created_at.isoformat() + "Z" if job.created_at else ""
    )

async def list_recent_jobs(db: AsyncSession, user_id: str, page: int = 1, page_size: int = 8) -> Paginated[Job]:
    from sqlalchemy import func
    
    if settings.USE_MOCKS:
        mock_job = Job(
            job_id="mock-job-id-123",
            status="succeeded",
            progress=1.0,
            stage="scoring",
            stage_label="Scoring Creatives",
            stage_index=4,
            stages_total=5,
            records_found=15,
            elapsed_ms=12000,
            created_at=datetime.datetime.utcnow().isoformat() + "Z"
        )
        return Paginated(
            items=[mock_job],
            total=1,
            page=page,
            page_size=page_size,
            has_more=False
        )

    # Count total jobs
    count_query = select(func.count(ScrapeJob.id)).join(
        Organization, ScrapeJob.org_id == Organization.id
    ).where(Organization.owner_id == user_id)
    total = await db.scalar(count_query) or 0

    # Fetch jobs
    offset = (page - 1) * page_size
    query = select(ScrapeJob).join(
        Organization, ScrapeJob.org_id == Organization.id
    ).where(Organization.owner_id == user_id).order_by(
        ScrapeJob.created_at.desc()
    ).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    jobs = result.scalars().all()

    items = [
        Job(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            stage=job.stage or "",
            stage_label=job.stage_label or "",
            stage_index=job.stage_index or 0,
            stages_total=job.stages_total or 1,
            records_found=job.record_count or 0,
            elapsed_ms=job.elapsed_ms or 0,
            created_at=job.created_at.isoformat() + "Z" if job.created_at else ""
        )
        for job in jobs
    ]

    return Paginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total
    )

async def run_scrape_simulation(job_id: str, query: str):
    from app.models.creative import Creative as DBCreative
    from app.models.creative_score import CreativeScore as DBCreativeScore
    
    # Wait a bit
    await asyncio.sleep(1.0)
    
    async with async_session_maker() as db:
        result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return
            
        job.progress = 0.4
        job.stage = "scraping"
        job.stage_label = "Scraping Platforms"
        await db.commit()
        
    await asyncio.sleep(1.0)
    
    async with async_session_maker() as db:
        result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return
            
        job.progress = 0.8
        job.stage = "scoring"
        job.stage_label = "Scoring Creatives"
        await db.commit()
        
    await asyncio.sleep(1.0)
    
    async with async_session_maker() as db:
        result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return
            
        record_count = 0
        if "empty" not in query.lower():
            # Insert a creative
            c_id = f"creative-{job_id}-1"
            creative = DBCreative(
                id=c_id,
                job_id=job_id,
                brand_id="nike",
                platform="meta",
                format="video",
                headline="Just Do It!",
                body="Unlock your potential with our latest gear.",
                cta="Shop Now",
                impressions_est=150000,
                spend_band="high",
                engagement_rate=0.045,
                ctr_est=0.018,
                first_seen="2026-08-10T12:00:00Z",
                last_seen="2026-08-20T12:00:00Z",
                days_active=10,
                variant_count=2
            )
            db.add(creative)
            
            score = DBCreativeScore(
                creative_id=c_id,
                hook=88.5,
                clarity=92.0,
                retention=84.0,
                composite=87.5
            )
            db.add(score)
            record_count = 1
            
        job.progress = 1.0
        job.status = "succeeded"
        job.stage = "complete"
        job.stage_label = "Complete"
        job.record_count = record_count
        await db.commit()



