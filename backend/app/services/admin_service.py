from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.schemas.admin import AdminOverviewStats, AdminJobRow, AdminSystemHealth, AdminServiceHealth
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.core.config import settings
import datetime

async def get_overview(db: AsyncSession) -> AdminOverviewStats:
    if settings.USE_MOCKS:
        return AdminOverviewStats(
            organizations=10,
            active_scrape_jobs=2,
            system_health="operational",
            api_error_rate=0.01,
            window_label="Last 24h"
        )
    
    org_count = await db.scalar(select(func.count(Organization.id)))
    active_jobs = await db.scalar(select(func.count(ScrapeJob.id)).where(ScrapeJob.status == "running"))
    
    return AdminOverviewStats(
        organizations=org_count or 0,
        active_scrape_jobs=active_jobs or 0,
        system_health="operational",
        api_error_rate=0.0,
        window_label="Last 24h"
    )

async def list_jobs(db: AsyncSession) -> list[AdminJobRow]:
    if settings.USE_MOCKS:
        return [
            AdminJobRow(
                job_id="job-1",
                organization="Org A",
                query="Competitor X",
                status="running",
                records=100,
                duration_ms=60000,
                created_at=datetime.datetime.utcnow().isoformat() + "Z"
            )
        ]

    query = select(ScrapeJob, Organization).outerjoin(Organization, ScrapeJob.org_id == Organization.id).order_by(ScrapeJob.created_at.desc()).limit(20)
    result = await db.execute(query)
    rows = result.all()
    
    jobs = []
    for job, org in rows:
        jobs.append(AdminJobRow(
            job_id=job.id,
            organization=org.name if org else job.org_id,
            query=job.query,
            status=job.status,
            records=job.record_count,
            duration_ms=job.elapsed_ms,
            created_at=job.created_at.isoformat() + "Z" if job.created_at else ""
        ))
    return jobs

async def get_health(db: AsyncSession) -> AdminSystemHealth:
    if settings.USE_MOCKS:
        return AdminSystemHealth(
            state="operational",
            services=[
                AdminServiceHealth(
                    id="db-primary",
                    name="Primary Database",
                    status="success",
                    detail="Connected",
                    latency_ms=15,
                    last_checked=datetime.datetime.utcnow().isoformat() + "Z"
                )
            ]
        )

    db_status = "error"
    detail = "Disconnected"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "success"
        detail = "Connected"
    except Exception as e:
        detail = str(e)

    return AdminSystemHealth(
        state="operational" if db_status == "success" else "degraded",
        services=[
            AdminServiceHealth(
                id="db-primary",
                name="Primary Database",
                status=db_status,
                detail=detail,
                latency_ms=0,
                last_checked=datetime.datetime.utcnow().isoformat() + "Z"
            )
        ]
    )

