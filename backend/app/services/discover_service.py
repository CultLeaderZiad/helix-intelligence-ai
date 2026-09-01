from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from sqlalchemy import select, func
from fastapi import HTTPException, BackgroundTasks
import datetime
import asyncio
import traceback
import uuid
import time
import os

from app.schemas.discover import SearchParams, Job
from app.schemas.common import Paginated
from app.models.scrape_job import ScrapeJob
from app.models.organization import Organization
from app.models.user import User
from app.core.config import settings
from app.db.session import async_session_maker

from app.services.scraping.ad_library_provider import AdLibraryProvider, DISCOVERY_PROVIDER_CHAIN
from app.services.scraping.scrapegraph_provider import ScrapeGraphProvider
from app.services.scraping.normalizer import normalize_creative
from app.services.creative_service import generate_patterns_for_recent_creatives
from app.services.billing_service import (
    get_or_create_default_org,
    assert_can_spend,
    charge,
    refund,
    DISCOVER_SEARCH_CREDIT_COST,
    DISCOVER_DEEP_SEARCH_CREDIT_COST,
    ESTIMATED_PROVIDER_COSTS
)
from app.services.api_usage_service import (
    check_global_cap_and_log_preflight,
    mark_api_usage_status,
    APILimitExceeded
)

async def trigger_search(
    db: AsyncSession,
    search_params: SearchParams,
    user_id: str,
    background_tasks: Optional[BackgroundTasks] = None
) -> Job:
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
    
    # 1. Fetch user
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    org = await get_or_create_default_org(db, user)
    org_id = org.id
    clean_query = search_params.query.strip()

    # 2. 12-Hour Query Deduplication Cache Check
    # If identical query was already scraped successfully in this org in the last 12h,
    # return the cached result immediately (0 credits required, 0 credits charged).
    twelve_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=12)
    duplicate_job_result = await db.execute(
        select(ScrapeJob)
        .where(ScrapeJob.org_id == org_id)
        .where(ScrapeJob.query == clean_query)
        .where(ScrapeJob.status == "succeeded")
        .where(ScrapeJob.created_at >= twelve_hours_ago)
        .order_by(ScrapeJob.created_at.desc())
        .limit(1)
    )
    duplicate_job = duplicate_job_result.scalar_one_or_none()
    if duplicate_job:
        return Job(
            job_id=duplicate_job.id,
            status=duplicate_job.status,
            progress=duplicate_job.progress,
            stage=duplicate_job.stage,
            stage_label=duplicate_job.stage_label,
            stage_index=duplicate_job.stage_index,
            stages_total=duplicate_job.stages_total,
            records_found=duplicate_job.record_count,
            elapsed_ms=duplicate_job.elapsed_ms,
            created_at=duplicate_job.created_at.isoformat() + "Z" if duplicate_job.created_at else ""
        )

    # 3. Server-side Quota & Feature Gatekeeper (with row-level locking)
    org, plan = await assert_can_spend(
        db,
        user=user,
        required_credits=DISCOVER_SEARCH_CREDIT_COST,
        feature_name="discover",
        lock_row=True
    )

    # 4. Create new ScrapeJob
    new_job = ScrapeJob(
        org_id=org_id,
        query=clean_query,
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

    # 5. Upfront Base Charge (2.0 Credits)
    await charge(
        db=db,
        org=org,
        user_id=user.id,
        amount=DISCOVER_SEARCH_CREDIT_COST,
        provider="discover_composite",
        operation="discover_job_start",
        units=1.0,
        cost_usd=ESTIMATED_PROVIDER_COSTS.get("apify_ad", 0.00075) * 15,
        job_id=new_job.id,
        metadata={"query": clean_query}
    )

    if background_tasks:
        background_tasks.add_task(run_discovery_pipeline, new_job.id, clean_query, search_params.filters)
    else:
        asyncio.create_task(run_discovery_pipeline(new_job.id, clean_query, search_params.filters))

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
        progress=job.progress or 0.0,
        stage=job.stage or "complete",
        stage_label=job.stage_label or "Complete",
        stage_index=job.stage_index or 0,
        stages_total=job.stages_total or 1,
        records_found=job.record_count or 0,
        elapsed_ms=job.elapsed_ms or 0,
        created_at=job.created_at.isoformat() + "Z" if job.created_at else "",
        completed_at=job.completed_at.isoformat() + "Z" if job.completed_at else None,
        error=job.error_msg
    )

async def list_recent_jobs(db: AsyncSession, user_id: str, page: int = 1, page_size: int = 8) -> Paginated[Job]:
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
            created_at=datetime.datetime.utcnow().isoformat() + "Z",
            completed_at=datetime.datetime.utcnow().isoformat() + "Z"
        )
        return Paginated(
            items=[mock_job],
            total=1,
            page=page,
            page_size=page_size,
            has_more=False
        )

    count_query = select(func.count(ScrapeJob.id)).join(
        Organization, ScrapeJob.org_id == Organization.id
    ).where(Organization.owner_id == user_id)
    total = await db.scalar(count_query) or 0

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
            completed_at=job.completed_at.isoformat() + "Z" if job.completed_at else None,
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

async def run_discovery_pipeline(job_id: str, query: str, filters: dict = None):
    start_time = time.time()
    async with async_session_maker() as db:
        result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return
        org_id = job.org_id
        
    usage_log_id = None
    sources_tried: List[str] = []
    
    try:
        # Pre-flight Check & Global Cap
        async with async_session_maker() as db:
            org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one()
            user_id = org.owner_id
            
            usage_log = await check_global_cap_and_log_preflight(
                db=db,
                provider="discover_composite",
                org_id=org_id,
                user_id=user_id,
                query=query,
                max_records=15,
                estimated_cost=0.01
            )
            usage_log_id = usage_log.id

        # Stage 1: Canonical Ad Library Scraper Chain
        async with async_session_maker() as db:
            await update_job_stage(db, job_id, "scraping", "Scraping Platforms", 0.2, 1)
        
        async def on_scraping_progress(elapsed_s: int, msg: str):
            async with async_session_maker() as db:
                result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
                j = result.scalar_one_or_none()
                if j:
                    j.stage_label = msg
                    j.elapsed_ms = int((time.time() - start_time) * 1000)
                    await db.commit()

        # Execute Canonical Ad Discovery Chain (Metapi -> Adyntel -> Meta Official -> Apify)
        ad_lib_provider = AdLibraryProvider(db, str(org_id), str(user_id))
        raw_creatives = await ad_lib_provider.search(
            query,
            max_records=15,
            filters=filters,
            progress_callback=on_scraping_progress
        )
        provider_used = ad_lib_provider.last_provider_used
        sources_tried = ad_lib_provider.sources_tried
            
        # Zero Results Handling (Honest reporting)
        if not raw_creatives:
            async with async_session_maker() as db:
                result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    sources_str = ", ".join(sources_tried) if sources_tried else "available sources"
                    job.status = "succeeded"
                    job.stage = "zero_results"
                    job.stage_label = f"No active ads found across [{sources_str}] for '{query}'. Try a company domain (e.g. 'nike.com') or general industry keyword."
                    job.progress = 1.0
                    job.stage_index = 5
                    job.record_count = 0
                    job.elapsed_ms = int((time.time() - start_time) * 1000)
                    job.completed_at = datetime.datetime.utcnow()
                    await db.commit()
            return
            
        # Stage 2: Enriching with ScrapeGraph (Capped at top 2 landing pages)
        async with async_session_maker() as db:
            await update_job_stage(db, job_id, "enriching", "Enriching via Landing Pages", 0.4, 2)
            
        scrapegraph = ScrapeGraphProvider()
        enriched_creatives = []
        scrapegraph_calls = 0
        for rc in raw_creatives:
            if rc.landing_url and scrapegraph_calls < 2:
                extra_data = await scrapegraph.extract_landing_page(rc.landing_url)
                enriched_creatives.append((rc, extra_data))
                scrapegraph_calls += 1
            else:
                enriched_creatives.append((rc, None))
                
        # Stage 3: Normalizing and Saving to DB
        async with async_session_maker() as db:
            await update_job_stage(db, job_id, "normalizing", "Normalizing & Saving", 0.6, 3)
            brand_id = str(uuid.uuid4())
            saved_creatives = 0
            for rc, extra in enriched_creatives:
                db_creative, db_score = normalize_creative(rc, job_id, brand_id, extra)
                db.add(db_creative)
                db.add(db_score)
                saved_creatives += 1
            await db.commit()
            
        # Stage 4: AI Pattern Scoring/Generation (Graceful Degradation)
        async with async_session_maker() as db:
            await update_job_stage(db, job_id, "scoring", "AI Generating Insights", 0.8, 4)
            org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one()
            user = (await db.execute(select(User).where(User.id == org.owner_id))).scalar_one()
            try:
                await generate_patterns_for_recent_creatives(db, user, job_id)
            except HTTPException as he:
                # If trial expired or plan restricted, gracefully preserve the scraped creatives
                detail = he.detail if isinstance(he.detail, dict) else {"message": str(he.detail)}
                err_code = detail.get("error") or detail.get("code") or "plan_restricted"
                print(f"[DiscoverPipeline] AI pattern scoring gracefully skipped for job {job_id}: {err_code} - {detail.get('message')}")
            except Exception as ai_err:
                print(f"[DiscoverPipeline] AI pattern scoring encountered an issue for job {job_id}: {ai_err}")
            
        # Stage 5: Complete
        async with async_session_maker() as db:
            result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = "succeeded"
                job.stage = "complete"
                job.stage_label = "Complete"
                job.progress = 1.0
                job.stage_index = 5
                job.record_count = saved_creatives
                job.elapsed_ms = int((time.time() - start_time) * 1000)
                job.completed_at = datetime.datetime.utcnow()
                await db.commit()
            
            if usage_log_id:
                await mark_api_usage_status(db, usage_log_id, "success")
                
    except APILimitExceeded as e:
        error_msg = str(e)
        print(f"Pipeline blocked: {error_msg}")
        async with async_session_maker() as db:
            result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error_msg = error_msg
                job.elapsed_ms = int((time.time() - start_time) * 1000)
                await db.commit()
            if usage_log_id:
                await mark_api_usage_status(db, usage_log_id, "failed")
            # Refund initial credits on pre-flight block
            await refund(db, org_id, DISCOVER_SEARCH_CREDIT_COST, "api_limit_preflight", job_id)
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
            if usage_log_id:
                await mark_api_usage_status(db, usage_log_id, "failed")
