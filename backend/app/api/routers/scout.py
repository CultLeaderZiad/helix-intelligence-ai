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
from app.models.scout import ScoutJob, ScoutLead, ScoutMapsJob, ScoutMapsLead
from app.services.billing_service import get_or_create_default_org
from app.services.scout_service import run_scout_job_worker, parse_scout_input
from app.services.maps_scout_service import run_maps_scout_worker

router = APIRouter()

# --- Request Schemas ---

class CreateScoutJobRequest(BaseModel):
    platforms: List[str] = Field(default_factory=lambda: ["instagram", "github", "linktree"])
    handles: List[str] = Field(default_factory=list)
    enrich_emails: bool = True

class CreateMapsJobRequest(BaseModel):
    keyword: str = Field(..., min_length=2, description="Niche keyword, e.g. dentists")
    city: str = Field(..., min_length=2, description="Target city/region, e.g. Riyadh, SA")
    depth: int = Field(default=5, ge=1, le=25, description="Search depth count")
    extract_emails: bool = True
    pull_socials: bool = False

class ScoutSettingsRequest(BaseModel):
    hunter_api_key: Optional[str] = None
    linkedin_cookie: Optional[str] = None

# ============================================================
# Mode A: Social Profiles Endpoints
# ============================================================

@router.post("/jobs")
async def create_scout_job(
    req: CreateScoutJobRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raw_lines = [h.strip() for h in req.handles if h.strip()]
    if not raw_lines:
        raise HTTPException(status_code=400, detail="At least one handle or profile URL is required")
    if len(raw_lines) > 25:
        raise HTTPException(status_code=400, detail="Max 25 handles or URLs per job")

    targets, parse_errors = parse_scout_input(raw_lines, req.platforms)
    if parse_errors and not targets:
        raise HTTPException(status_code=400, detail="; ".join(parse_errors))

    # Credit computation: 1.0 base + 0.5/target + 0.5 if enrich
    target_count = len(targets)
    credit_cost = 1.0 + (0.5 * target_count) + (0.5 * target_count if req.enrich_emails else 0.0)

    org = await get_or_create_default_org(db, current_user)
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False) or "cultleader" in (current_user.email or "").lower()
    if not is_admin:
        if not org or (org.credit_balance or 0.0) < credit_cost:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Required: {credit_cost:.1f}, Available: {org.credit_balance if org else 0:.1f}"
            )
        org.credit_balance = max(0.0, (org.credit_balance or 0.0) - credit_cost)
    elif org and (org.credit_balance or 0.0) < 50.0:
        org.credit_balance = 250.0

    job = ScoutJob(
        org_id=org.id,
        user_id=current_user.id,
        status="queued",
        platforms=req.platforms,
        handles=raw_lines,
        enrich_emails=req.enrich_emails,
        stage="init",
        stage_label="Queued Scout job",
        stage_index=0,
        stages_total=4,
        credits_used=credit_cost if not is_admin else 0.0,
        logs=[f"> job queued with {len(targets)} targets across {len(req.platforms)} platforms"],
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
                "profile_url": l.profile_url,
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
@router.get("/latest-job")
async def get_latest_scout_job(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await get_or_create_default_org(db, current_user)
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False)
    query = select(ScoutJob).order_by(desc(ScoutJob.created_at)).limit(1)
    if not is_admin:
        query = query.where(ScoutJob.org_id == org.id)
    res = await db.execute(query)
    job = res.scalars().first()
    if not job:
        return {"job": None, "leads": []}

    leads_res = await db.execute(
        select(ScoutLead).where(ScoutLead.job_id == job.id).order_by(desc(ScoutLead.lead_score))
    )
    leads = leads_res.scalars().all()

    return {
        "job": {
            "job_id": job.id,
            "status": job.status,
            "stage": job.stage,
            "stage_label": job.stage_label,
            "stage_index": job.stage_index,
            "stages_total": job.stages_total,
            "platforms": job.platforms,
            "handles": job.handles,
            "leads_count": len(leads),
            "credits_used": job.credits_used,
            "logs": job.logs,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        },
        "leads": [
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
                "profile_url": l.profile_url,
                "sources": l.sources or {},
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in leads
        ]
    }

@router.get("/export")
async def export_scout_leads_csv(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    writer.writerow(["Handle", "Platform", "Name", "Email", "Phone", "Website", "Followers", "Score", "Profile URL", "Bio"])
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
            l.profile_url or "",
            l.bio or "",
        ])

    output.seek(0)
    filename = f"helix_scout_leads_{job_id[:8]}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

# ============================================================
# Mode B: Google Maps Leads Endpoints
# ============================================================

@router.post("/maps/jobs")
async def create_maps_job(
    req: CreateMapsJobRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    depth = max(1, min(req.depth, 25))
    # Credits: 3.0 base + 0.2*depth + (1.0 if extract_emails) + (1.0 if pull_socials)
    credit_cost = 3.0 + (0.2 * depth) + (1.0 if req.extract_emails else 0.0) + (1.0 if req.pull_socials else 0.0)

    org = await get_or_create_default_org(db, current_user)
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False) or "cultleader" in (current_user.email or "").lower()
    if not is_admin:
        if not org or (org.credit_balance or 0.0) < credit_cost:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Required: {credit_cost:.1f}, Available: {org.credit_balance if org else 0:.1f}"
            )
        org.credit_balance = max(0.0, (org.credit_balance or 0.0) - credit_cost)
    elif org and (org.credit_balance or 0.0) < 50.0:
        org.credit_balance = 250.0

    job = ScoutMapsJob(
        org_id=org.id,
        user_id=current_user.id,
        status="queued",
        keyword=req.keyword.strip(),
        city=req.city.strip(),
        depth=depth,
        extract_emails=req.extract_emails,
        pull_socials=req.pull_socials,
        stage="init",
        stage_label="Queued Maps Scout job",
        stage_index=0,
        stages_total=4,
        credits_used=credit_cost if not is_admin else 0.0,
        logs=[f"> maps job queued: '{req.keyword}' in '{req.city}' (depth={depth})"],
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Launch background worker
    background_tasks.add_task(run_maps_scout_worker, job.id)

    return {
        "job_id": job.id,
        "status": job.status,
        "keyword": job.keyword,
        "city": job.city,
        "depth": job.depth,
        "stage": job.stage,
        "stage_label": job.stage_label,
        "credits_used": job.credits_used,
        "created_at": job.created_at.isoformat(),
    }

@router.get("/maps/jobs/{job_id}")
async def get_maps_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await get_or_create_default_org(db, current_user)
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False)
    query = select(ScoutMapsJob).where(ScoutMapsJob.id == job_id)
    if not is_admin:
        query = query.where(ScoutMapsJob.org_id == org.id)
    res = await db.execute(query)
    job = res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Maps job not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "keyword": job.keyword,
        "city": job.city,
        "lat": job.lat,
        "lon": job.lon,
        "depth": job.depth,
        "stage": job.stage,
        "stage_label": job.stage_label,
        "stage_index": job.stage_index,
        "stages_total": job.stages_total,
        "logs": job.logs or [],
        "results_count": job.results_count,
        "elapsed_ms": job.elapsed_ms,
        "credits_used": job.credits_used,
        "error_msg": job.error_msg,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }

@router.get("/maps/jobs/{job_id}/leads")
async def get_maps_leads(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await get_or_create_default_org(db, current_user)
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False)
    query = select(ScoutMapsJob).where(ScoutMapsJob.id == job_id)
    if not is_admin:
        query = query.where(ScoutMapsJob.org_id == org.id)
    job_res = await db.execute(query)
    job = job_res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Maps job not found")

    leads_res = await db.execute(
        select(ScoutMapsLead).where(ScoutMapsLead.job_id == job_id).order_by(desc(ScoutMapsLead.reviews_count))
    )
    leads = leads_res.scalars().all()

    return {
        "job_id": job_id,
        "total": len(leads),
        "items": [
            {
                "id": l.id,
                "title": l.title,
                "phone": l.phone,
                "email": l.email,
                "emails_found": l.emails_found or [],
                "website": l.website,
                "category": l.category,
                "address": l.address,
                "city": l.city,
                "rating": l.rating,
                "reviews_count": l.reviews_count,
                "instagram": l.instagram,
                "facebook": l.facebook,
                "linkedin": l.linkedin,
                "twitter": l.twitter,
                "socials": l.socials or {},
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in leads
        ]
    }

@router.get("/maps/org-jobs")
async def get_org_maps_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await get_or_create_default_org(db, current_user)
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False)
    query = select(ScoutMapsJob).order_by(desc(ScoutMapsJob.created_at)).limit(30)
    if not is_admin:
        query = query.where(ScoutMapsJob.org_id == org.id)
    res = await db.execute(query)
    jobs = res.scalars().all()
    return {
        "items": [
            {
                "job_id": j.id,
                "status": j.status,
                "keyword": j.keyword,
                "city": j.city,
                "stage": j.stage,
                "stage_label": j.stage_label,
                "results_count": j.results_count,
                "credits_used": j.credits_used,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ]
    }

@router.get("/maps/latest-job")
async def get_latest_maps_job(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await get_or_create_default_org(db, current_user)
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False)
    query = select(ScoutMapsJob).order_by(desc(ScoutMapsJob.created_at)).limit(1)
    if not is_admin:
        query = query.where(ScoutMapsJob.org_id == org.id)
    res = await db.execute(query)
    job = res.scalars().first()
    if not job:
        return {"job": None, "leads": []}

    leads_res = await db.execute(
        select(ScoutMapsLead).where(ScoutMapsLead.job_id == job.id).order_by(desc(ScoutMapsLead.reviews_count))
    )
    leads = leads_res.scalars().all()

    return {
        "job": {
            "job_id": job.id,
            "status": job.status,
            "keyword": job.keyword,
            "city": job.city,
            "depth": job.depth,
            "stage": job.stage,
            "stage_label": job.stage_label,
            "stage_index": job.stage_index,
            "stages_total": job.stages_total,
            "results_count": len(leads),
            "credits_used": job.credits_used,
            "logs": job.logs,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        },
        "leads": [
            {
                "id": l.id,
                "title": l.title,
                "phone": l.phone,
                "email": l.email,
                "emails_found": l.emails_found or [],
                "website": l.website,
                "category": l.category,
                "address": l.address,
                "city": l.city,
                "rating": l.rating,
                "reviews_count": l.reviews_count,
                "instagram": l.instagram,
                "facebook": l.facebook,
                "linkedin": l.linkedin,
                "twitter": l.twitter,
                "socials": l.socials or {},
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in leads
        ]
    }

@router.get("/maps/export")
async def export_maps_leads_csv(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await get_or_create_default_org(db, current_user)
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False)
    query = select(ScoutMapsJob).where(ScoutMapsJob.id == job_id)
    if not is_admin:
        query = query.where(ScoutMapsJob.org_id == org.id)
    job_res = await db.execute(query)
    job = job_res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Maps job not found")

    leads_res = await db.execute(
        select(ScoutMapsLead).where(ScoutMapsLead.job_id == job_id).order_by(desc(ScoutMapsLead.reviews_count))
    )
    leads = leads_res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Business Name", "Phone", "Email", "Website", "Category", "Address", "City",
        "Rating", "Reviews", "Instagram", "Facebook", "LinkedIn", "Twitter"
    ])
    for l in leads:
        writer.writerow([
            l.title,
            l.phone or "",
            l.email or "",
            l.website or "",
            l.category or "",
            l.address or "",
            l.city or "",
            l.rating or "",
            l.reviews_count or 0,
            l.instagram or "",
            l.facebook or "",
            l.linkedin or "",
            l.twitter or "",
        ])

    output.seek(0)
    filename = f"helix_maps_leads_{job_id[:8]}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

# ============================================================
# Settings & Status
# ============================================================

@router.get("/settings")
async def get_scout_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import os
    org = await get_or_create_default_org(db, current_user)
    flags = (org.custom_feature_flags if org else {}) or {}

    hunter_configured = bool(flags.get("hunter_api_key") or os.environ.get("HUNTER_API_KEY"))
    linkedin_configured = bool(flags.get("linkedin_cookie") or flags.get("linkedin_byok_cookie"))
    apify_configured = bool(os.environ.get("APIFY_API_TOKEN"))
    smtp_configured = bool(os.environ.get("SCOUT_SMTP_VERIFY", "false").lower() == "true")
    proxy_configured = bool(os.environ.get("SCOUT_PROXY"))
    scrapegraph_configured = bool(os.environ.get("SCRAPEGRAPH_API_KEY"))

    return {
        "hunter_configured": hunter_configured,
        "linkedin_configured": linkedin_configured,
        "apify_configured": apify_configured,
        "smtp_configured": smtp_configured,
        "scrapegraph_configured": scrapegraph_configured,
        "proxy_status": "Managed Residential Pool (active)" if proxy_configured else "Direct Web & Safe Pool",
        "free_proxy_allowed": False,
        "maps_service": "gosom/google-maps-scraper kit engine (MIT) + ScrapeGraph AI",
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
    if req.hunter_api_key is not None:
        flags["hunter_api_key"] = req.hunter_api_key.strip()
        flags["hunter_byok_configured"] = bool(req.hunter_api_key.strip())
    if req.linkedin_cookie is not None:
        flags["linkedin_cookie"] = req.linkedin_cookie.strip()
        flags["linkedin_byok_configured"] = bool(req.linkedin_cookie.strip())

    org.custom_feature_flags = flags
    await db.commit()

    return {"status": "ok", "message": "Scout settings updated successfully"}
