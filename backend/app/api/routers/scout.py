import io
import csv
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.models.scout import ScoutJob, ScoutLead
from app.services.billing_service import get_or_create_default_org
from app.services.scout_service import run_scout_job_worker

router = APIRouter()

class CreateScoutJobRequest(BaseModel):
    platforms: List[str] = Field(default_factory=lambda: ["instagram", "github", "linktree"])
    handles: List[str] = Field(default_factory=list)
    enrich_emails: bool = True

class ScoutSettingsRequest(BaseModel):
    hunter_api_key: Optional[str] = None
    linkedin_cookie: Optional[str] = None

@router.post("/jobs")
async def create_scout_job(
    req: CreateScoutJobRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clean_handles = [h.strip().lstrip("@") for h in req.handles if h.strip()]
    if not clean_handles:
        raise HTTPException(status_code=400, detail="At least one handle is required")
    if len(clean_handles) > 25:
        raise HTTPException(status_code=400, detail="Max 25 handles per job")

    # Credit computation: 1.0 base + 0.5/handle + 0.5/enrich
    handle_count = len(clean_handles)
    credit_cost = 1.0 + (0.5 * handle_count) + (0.5 * handle_count if req.enrich_emails else 0.0)

    org = await get_or_create_default_org(db, current_user)
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False)
    if not is_admin:
        if not org or (org.credit_balance or 0.0) < credit_cost:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Required: {credit_cost:.1f}, Available: {org.credit_balance if org else 0:.1f}"
            )
        org.credit_balance = max(0.0, (org.credit_balance or 0.0) - credit_cost)

    job = ScoutJob(
        org_id=org.id,
        user_id=current_user.id,
        status="queued",
        platforms=req.platforms,
        handles=clean_handles,
        enrich_emails=req.enrich_emails,
        stage="init",
        stage_label="Queued Scout job",
        stage_index=0,
        stages_total=4,
        credits_used=credit_cost if not is_admin else 0.0,
        logs=[f"> job queued with {len(clean_handles)} handles across {len(req.platforms)} platforms"],
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Launch in background
    background_tasks.add_task(run_scout_job_worker, job.id)

    return {
        "job_id": job.id,
        "status": job.status,
        "stage": job.stage,
        "stage_label": job.stage_label,
        "credits_used": job.credits_used,
        "created_at": job.created_at.isoformat(),
    }

@router.get("/jobs/{job_id}")
async def get_scout_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await get_or_create_default_org(db, current_user)
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False)
    query = select(ScoutJob).where(ScoutJob.id == job_id)
    if not is_admin:
        query = query.where(ScoutJob.org_id == org.id)
    res = await db.execute(query)
    job = res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Scout job not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "stage": job.stage,
        "stage_label": job.stage_label,
        "stage_index": job.stage_index,
        "stages_total": job.stages_total,
        "logs": job.logs or [],
        "leads_count": job.leads_count,
        "elapsed_ms": job.elapsed_ms,
        "credits_used": job.credits_used,
        "error_msg": job.error_msg,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }

@router.get("/jobs/{job_id}/leads")
async def get_scout_leads(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify job access
    org = await get_or_create_default_org(db, current_user)
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False)
    query = select(ScoutJob).where(ScoutJob.id == job_id)
    if not is_admin:
        query = query.where(ScoutJob.org_id == org.id)
    job_res = await db.execute(query)
    job = job_res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Scout job not found")

    leads_res = await db.execute(
        select(ScoutLead).where(ScoutLead.job_id == job_id).order_by(desc(ScoutLead.lead_score))
    )
    leads = leads_res.scalars().all()

    return {
        "job_id": job_id,
        "total": len(leads),
        "items": [
            {
                "id": l.id,
                "handle": l.handle,
                "platform": l.platform,
                "name": l.name,
                "email": l.email,
                "phone": l.phone,
                "website": l.website,
                "bio": l.bio,
                "followers": l.followers,
                "lead_score": l.lead_score,
                "sources": l.sources or {},
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in leads
        ]
    }

@router.get("/org-jobs")
async def get_org_scout_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await get_or_create_default_org(db, current_user)
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False)
    query = select(ScoutJob).order_by(desc(ScoutJob.created_at)).limit(30)
    if not is_admin:
        query = query.where(ScoutJob.org_id == org.id)
    res = await db.execute(query)
    jobs = res.scalars().all()
    return {
        "items": [
            {
                "job_id": j.id,
                "status": j.status,
                "stage": j.stage,
                "stage_label": j.stage_label,
                "handles_count": len(j.handles or []),
                "leads_count": j.leads_count,
                "credits_used": j.credits_used,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ]
    }

@router.get("/export")
async def export_scout_leads_csv(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify job access
    org = await get_or_create_default_org(db, current_user)
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False)
    query = select(ScoutJob).where(ScoutJob.id == job_id)
    if not is_admin:
        query = query.where(ScoutJob.org_id == org.id)
    job_res = await db.execute(query)
    job = job_res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Scout job not found")

    leads_res = await db.execute(
        select(ScoutLead).where(ScoutLead.job_id == job_id).order_by(desc(ScoutLead.lead_score))
    )
    leads = leads_res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Handle", "Platform", "Name", "Email", "Phone", "Website", "Followers", "Score", "Bio"])
    for l in leads:
        writer.writerow([
            l.handle,
            l.platform,
            l.name or "",
            l.email or "",
            l.phone or "",
            l.website or "",
            l.followers or 0,
            l.lead_score or 0,
            l.bio or "",
        ])

    output.seek(0)
    filename = f"helix_scout_leads_{job_id[:8]}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

@router.get("/settings")
async def get_scout_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await get_or_create_default_org(db, current_user)
    flags = (org.custom_feature_flags if org else {}) or {}

    return {
        "hunter_configured": bool(flags.get("hunter_byok_configured")),
        "linkedin_configured": bool(flags.get("linkedin_byok_configured")),
        "smtp_configured": False,
        "proxy_status": "Managed Residential Pool (active)",
        "free_proxy_allowed": False,
    }

@router.post("/settings")
async def update_scout_settings(
    req: ScoutSettingsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await get_or_create_default_org(db, current_user)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    flags = dict(org.custom_feature_flags or {})
    if req.hunter_api_key:
        flags["hunter_byok_configured"] = True
    if req.linkedin_cookie:
        flags["linkedin_byok_configured"] = True

    org.custom_feature_flags = flags
    await db.commit()

    return {"status": "ok", "message": "Scout settings updated successfully"}
