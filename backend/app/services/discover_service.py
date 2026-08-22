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
import traceback
import uuid
import time
from app.services.scraping.ad_library_provider import AdLibraryProvider
from app.services.scraping.scrapegraph_provider import ScrapeGraphProvider
from app.services.scraping.normalizer import normalize_creative
from app.services.creative_service import generate_patterns_for_recent_creatives

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
    
    if not org:
        raise HTTPException(status_code=400, detail="No organization found for this user. Please contact support.")
    org_id = org.id
    

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
        background_tasks.add_task(run_discovery_pipeline, new_job.id, search_params.query)

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
        created_at=job.created_at.isoformat() + "Z" if job.created_at else "",
        error=job.error_msg
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
            created_at=job.created_at.isoformat() + "Z" if job.created_at else "",
            error=job.error_msg
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

async def update_job_stage(db: AsyncSession, job_id: str, stage: str, label: str, progress: float, stage_index: int):
    result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
    job = result.scalar_one_or_none()
    if job:
        job.stage = stage
        job.stage_label = label
        job.progress = progress
        job.stage_index = stage_index
        await db.commit()

async def run_discovery_pipeline(job_id: str, query: str):
    start_time = time.time()
    async with async_session_maker() as db:
        result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return
        
        org_id = job.org_id
        
    try:
        # Stage 1: Scraping Ad Library
        async with async_session_maker() as db:
            await update_job_stage(db, job_id, "scraping", "Scraping Platforms", 0.2, 1)
        
        ad_library = AdLibraryProvider()
        raw_creatives = await ad_library.search(query)
        
        if not raw_creatives:
            async with async_session_maker() as db:
                result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.status = "succeeded"
                    job.stage = "complete"
                    job.stage_label = "Complete"
                    job.progress = 1.0
                    job.stage_index = 5
                    job.record_count = 0
                    job.elapsed_ms = int((time.time() - start_time) * 1000)
                    job.completed_at = datetime.datetime.utcnow()
                    await db.commit()
            return
            
        # Stage 2: Enriching with ScrapeGraph
        async with async_session_maker() as db:
            await update_job_stage(db, job_id, "enriching", "Enriching via Landing Pages", 0.4, 2)
            
        scrapegraph = ScrapeGraphProvider()
        enriched_creatives = []
        for rc in raw_creatives:
            if rc.landing_url:
                extra_data = await scrapegraph.extract_landing_page(rc.landing_url)
                enriched_creatives.append((rc, extra_data))
            else:
                enriched_creatives.append((rc, None))
                
        # Stage 3: Normalizing and Saving to DB
        async with async_session_maker() as db:
            await update_job_stage(db, job_id, "normalizing", "Normalizing & Saving", 0.6, 3)
            
            brand_id = str(uuid.uuid4()) # For now, mock a brand UUID for the query
            
            saved_creatives = 0
            for rc, extra in enriched_creatives:
                db_creative, db_score = normalize_creative(rc, job_id, brand_id, extra)
                db.add(db_creative)
                db.add(db_score)
                saved_creatives += 1
                
            await db.commit()
            
        # Stage 4: AI Pattern Scoring/Generation
        async with async_session_maker() as db:
            await update_job_stage(db, job_id, "scoring", "AI Generating Insights", 0.8, 4)
            # Fetch the user for the org
            from app.models.organization import Organization
            from app.models.user import User
            org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one()
            user = (await db.execute(select(User).where(User.id == org.owner_id))).scalar_one()
            await generate_patterns_for_recent_creatives(db, user, job_id)
            
        # Stage 5: Complete
        async with async_session_maker() as db:
            result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
            job = result.scalar_one_or_none()
            job.status = "succeeded"
            job.stage = "complete"
            job.stage_label = "Complete"
            job.progress = 1.0
            job.stage_index = 5
            job.record_count = saved_creatives
            job.elapsed_ms = int((time.time() - start_time) * 1000)
            job.completed_at = datetime.datetime.utcnow()
            await db.commit()
            
    except Exception as e:
        error_msg = f"Pipeline failed: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        async with async_session_maker() as db:
            result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error_msg = str(e)
                job.elapsed_ms = int((time.time() - start_time) * 1000)
                await db.commit()
