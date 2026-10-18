import io
import csv
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from datetime import datetime, timezone
from app.core.runtime import BOOT_ID
from app.core.deps import get_db, get_current_user, require_feature
from app.models.user import User
from app.models.scout import ScoutJob, ScoutLead, ScoutMapsJob, ScoutMapsLead
from app.services.billing_service import (
    get_or_create_default_org,
    assert_can_spend,
    charge,
    get_idempotent_operation,
)
from app.services.scout_service import run_scout_job_worker
from app.services.scout_parse import parse_input_targets
from app.services.maps_scout_service import run_maps_scout_worker

router = APIRouter(dependencies=[Depends(require_feature("scout"))])


def sanitize_csv_cell(val: object) -> object:
    """Neutralize spreadsheet formula injection (OWASP CWE-1236)."""
    if val is None:
        return ""
    if isinstance(val, str):
        if val and val[0] in ("=", "+", "-", "@", "\t", "\r"):
            return f"'{val}"
        return val
    return val

# --- Request Schemas ---

class CreateScoutJobRequest(BaseModel):
    platforms: List[str] = Field(default_factory=lambda: ["instagram", "github", "linktree"])
    handles: List[str] = Field(default_factory=list)
    enrich_emails: bool = True
    target_category: Optional[str] = None
    generate_outreach: bool = True

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
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
):
    key = idempotency_key or x_idempotency_key
    if key:
        org = await get_or_create_default_org(db, current_user, lock_row=False)
        existing_log = await get_idempotent_operation(db, org.id, key, "scout_job_start")
        if existing_log and existing_log.job_id:
            existing_job = (await db.execute(
                select(ScoutJob).where(ScoutJob.id == existing_log.job_id)
            )).scalar_one_or_none()
            if existing_job:
                return {
                    "job_id": existing_job.id,
                    "status": existing_job.status,
                    "stage": existing_job.stage,
                    "stage_label": existing_job.stage_label,
                    "credits_used": existing_job.credits_used,
                    "created_at": existing_job.created_at.isoformat() if existing_job.created_at else None,
                    "idempotent_replay": True,
                }

    raw_lines = [h.strip() for h in req.handles if h.strip()]
    if not raw_lines:
        raise HTTPException(status_code=400, detail="At least one handle or profile URL is required")
    if len(raw_lines) > 25:
        raise HTTPException(status_code=400, detail="Max 25 handles or URLs per job")

    try:
        targets = parse_input_targets(raw_lines, req.platforms)
    except ValueError as parse_err:
        raise HTTPException(status_code=400, detail=str(parse_err))

    if not targets:
        raise HTTPException(status_code=400, detail="No valid handles or URLs provided")

    # Credit computation: 1.0 base + 0.5/target + 0.5 if enrich
    target_count = len(targets)
    credit_cost = 1.0 + (0.5 * target_count) + (0.5 * target_count if req.enrich_emails else 0.0)

    # SECURITY: admins bypass by ROLE ONLY. The previous email-substring check
    # ("cultleader" in email) let any self-registered address run free work and
    # auto-refill the balance to 250 credits. Removed.
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False)
    if is_admin:
        org = await get_or_create_default_org(db, current_user)
    else:
        # Central, row-locked gatekeeper: trial expiry, feature flags, daily
        # caps, and credit balance - no direct balance writes.
        org, _plan = await assert_can_spend(
            db, current_user, required_credits=credit_cost, feature_name="scout", lock_row=True
        )

    job = ScoutJob(
        org_id=org.id,
        user_id=current_user.id,
        status="queued",
        platforms=req.platforms,
        handles=raw_lines,
        enrich_emails=req.enrich_emails,
        target_category=req.target_category.strip() if req.target_category else None,
        generate_outreach=req.generate_outreach,
        stage="init",
        stage_label="Queued Scout Atlas job",
        stage_index=0,
        stages_total=4,
        credits_used=credit_cost if not is_admin else 0.0,
        owner_boot_id=BOOT_ID,
        heartbeat_at=datetime.now(timezone.utc),
        logs=[f"> job queued with {len(targets)} targets (category: {req.target_category or 'general'})"],
    )
    db.add(job)
    await db.flush()

    # Launch in background after the job and the credit reservation commit together.
    if not is_admin:
        usage = await charge(
            db=db, org=org, user_id=current_user.id, amount=credit_cost,
            provider="scout_social", operation="scout_job_start", units=1.0,
            cost_usd=0.0, job_id=job.id, metadata={"targets": target_count},
            idempotency_key=key,
        )
        if usage.job_id and usage.job_id != job.id:
            await db.rollback()
            existing_job = (
                await db.execute(select(ScoutJob).where(ScoutJob.id == usage.job_id))
            ).scalar_one_or_none()
            if existing_job:
                return {
                    "job_id": existing_job.id,
                    "status": existing_job.status,
                    "stage": existing_job.stage,
                    "stage_label": existing_job.stage_label,
                    "credits_used": existing_job.credits_used,
                    "created_at": existing_job.created_at.isoformat() if existing_job.created_at else None,
                    "idempotent_replay": True,
                }
    else:
        await db.commit()
    await db.refresh(job)

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
                "scrape_status": l.scrape_status or "ok",
                "account_type": getattr(l, "account_type", None) or (l.atlas or {}).get("profile_analysis", {}).get("account_type"),
                "priority_level": getattr(l, "priority_level", None) or (l.atlas or {}).get("lead_scoring", {}).get("priority_level"),
                "atlas": l.atlas or {},
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
            "target_category": job.target_category,
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
                "scrape_status": l.scrape_status or "ok",
                "atlas": l.atlas or {},
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
    writer.writerow([
        "Handle", "Platform", "Name", "Score", "Priority", "Account Type", "Primary Niche",
        "Email", "Email Source", "Phone", "Website", "Followers", "Scrape Status",
        "Outreach Subject", "Outreach Email Body", "Profile URL", "Bio"
    ])
    for l in leads:
        atlas = l.atlas or {}
        outreach = atlas.get("outreach", {}) or {}
        analysis = atlas.get("profile_analysis", {}) or {}
        scoring = atlas.get("lead_scoring", {}) or {}
        writer.writerow([sanitize_csv_cell(x) for x in [
            l.handle,
            l.platform,
            l.name or "",
            l.lead_score or 0,
            scoring.get("priority_level") or "low",
            analysis.get("account_type") or "unknown",
            analysis.get("primary_niche") or "",
            l.email or "",
            (l.sources or {}).get("email_source") or "",
            l.phone or "",
            l.website or "",
            l.followers or 0,
            l.scrape_status or "ok",
            outreach.get("email_subject") or "",
            outreach.get("email_body") or "",
            l.profile_url or "",
            l.bio or "",
        ]])

    output.seek(0)
    filename = f"helix_scout_atlas_leads_{job_id[:8]}.csv"
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
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
):
    key = idempotency_key or x_idempotency_key
    if key:
        org = await get_or_create_default_org(db, current_user, lock_row=False)
        existing_log = await get_idempotent_operation(db, org.id, key, "scout_maps_job_start")
        if existing_log and existing_log.job_id:
            existing_job = (await db.execute(
                select(ScoutMapsJob).where(ScoutMapsJob.id == existing_log.job_id)
            )).scalar_one_or_none()
            if existing_job:
                return {
                    "job_id": existing_job.id,
                    "status": existing_job.status,
                    "keyword": existing_job.keyword,
                    "city": existing_job.city,
                    "depth": existing_job.depth,
                    "stage": existing_job.stage,
                    "stage_label": existing_job.stage_label,
                    "credits_used": existing_job.credits_used,
                    "created_at": existing_job.created_at.isoformat() if existing_job.created_at else None,
                    "idempotent_replay": True,
                }

    depth = max(1, min(req.depth, 25))
    # Credits: 3.0 base + 0.2*depth + (1.0 if extract_emails) + (1.0 if pull_socials)
    credit_cost = 3.0 + (0.2 * depth) + (1.0 if req.extract_emails else 0.0) + (1.0 if req.pull_socials else 0.0)

    # SECURITY: admins bypass by ROLE ONLY. The previous email-substring check
    # ("cultleader" in email) let any self-registered address run free work and
    # auto-refill the balance to 250 credits. Removed.
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False)
    if is_admin:
        org = await get_or_create_default_org(db, current_user)
    else:
        # Central, row-locked gatekeeper: trial expiry, feature flags, daily
        # caps, and credit balance - no direct balance writes.
        org, _plan = await assert_can_spend(
            db, current_user, required_credits=credit_cost, feature_name="scout", lock_row=True
        )

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
        owner_boot_id=BOOT_ID,
        heartbeat_at=datetime.now(timezone.utc),
        logs=[f"> maps job queued: '{req.keyword}' in '{req.city}' (depth={depth})"],
    )
    db.add(job)
    await db.flush()

    # Launch background worker after the job and the credit reservation commit together.
    if not is_admin:
        usage = await charge(
            db=db, org=org, user_id=current_user.id, amount=credit_cost,
            provider="scout_maps", operation="scout_maps_job_start", units=1.0,
            cost_usd=0.0, job_id=job.id,
            metadata={"keyword": req.keyword, "city": req.city, "depth": depth},
            idempotency_key=key,
        )
        if usage.job_id and usage.job_id != job.id:
            await db.rollback()
            existing_job = (
                await db.execute(select(ScoutMapsJob).where(ScoutMapsJob.id == usage.job_id))
            ).scalar_one_or_none()
            if existing_job:
                return {
                    "job_id": existing_job.id,
                    "status": existing_job.status,
                    "keyword": existing_job.keyword,
                    "city": existing_job.city,
                    "credits_used": existing_job.credits_used,
                    "created_at": existing_job.created_at.isoformat() if existing_job.created_at else None,
                    "idempotent_replay": True,
                }
    else:
        await db.commit()
    await db.refresh(job)

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
        writer.writerow([sanitize_csv_cell(x) for x in [
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
        ]])

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
    smtp_configured = bool(os.environ.get("SCOUT_SMTP_VERIFY", "false").lower() == "true")
    proxy_configured = bool(os.environ.get("SCOUT_PROXY"))
    scrapegraph_configured = bool(os.environ.get("SCRAPEGRAPH_API_KEY"))

    return {
        "hunter_configured": hunter_configured,
        "linkedin_configured": linkedin_configured,
        "smtp_configured": smtp_configured,
        "scrapegraph_configured": scrapegraph_configured,
        "proxy_status": "Managed Residential Pool (active)" if proxy_configured else "Direct Web & Safe Pool",
        "free_proxy_allowed": False,
        "engine": "kiryano/Scout OSS (MIT) + Helix Atlas Pipeline",
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
    from app.core.tenancy import require_org_manager
    await require_org_manager(db, org, current_user)

    from app.services.security_service import encrypt_secret
    flags = dict(org.custom_feature_flags or {})
    if req.hunter_api_key is not None:
        raw_key = req.hunter_api_key.strip()
        flags["hunter_api_key"] = encrypt_secret(raw_key) if raw_key else ""
        flags["hunter_byok_configured"] = bool(raw_key)
    if req.linkedin_cookie is not None:
        raw_cookie = req.linkedin_cookie.strip()
        flags["linkedin_cookie"] = encrypt_secret(raw_cookie) if raw_cookie else ""
        flags["linkedin_byok_configured"] = bool(raw_cookie)

    org.custom_feature_flags = flags
    await db.commit()

    return {"status": "ok", "message": "Scout settings updated successfully"}
