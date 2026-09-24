"""Scout · Lead Generation router (engine: scrapling_engine).

Base mount: /api/v1/scout/leadgen

Contract rules (same honesty envelope as Social Scout):
- Long work returns a Job immediately; the worker claims it; UI polls.
- Never fabricate leads/logs. Worker offline -> honest 503 worker_offline.
- Credits charged at enqueue (admins bypass), org-scoped on every query.
- robots_txt_obey defaults ON; disabling writes an audit log line on the job.
"""
import io
import csv
import json
import ipaddress
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.leadgen import LeadGenJob, LeadGenLead, LeadGenWorkerHeartbeat
from app.schemas.leadgen import CreateLeadGenJobRequest, LeadGenJobEnvelope
from app.services.billing_service import get_or_create_default_org

logger = logging.getLogger(__name__)
router = APIRouter()

RECIPES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "leadgen_recipes"
STAGES_TOTAL = 9

# ---------------------------------------------------------------------------
# Seed validation (stage 4.2 -- enforced at enqueue for honest 400s;
# re-checked defensively by the pipeline)
# ---------------------------------------------------------------------------

_PRIVATE_HOST_RE = re.compile(r"^(localhost|.*\.(local|internal|localhost))$", re.IGNORECASE)


def _normalize_seed(raw: str) -> str:
    """Return an absolute http(s) URL or raise ValueError with a clear reason."""
    value = (raw or "").strip()
    if not value:
        raise ValueError("Empty seed URL")
    if "://" in value:
        scheme = value.split("://", 1)[0].lower()
        if scheme not in ("http", "https"):
            raise ValueError(f"Non-http(s) scheme rejected: {scheme}:// (only http/https are fetched)")
    else:
        value = "https://" + value

    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Non-http(s) scheme rejected: {parsed.scheme}://")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError(f"Seed has no host: {raw!r}")
    if host == "localhost" or _PRIVATE_HOST_RE.match(host):
        raise ValueError(f"Private/local host rejected: {host}")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError(f"Private/reserved IP rejected: {host}")
    except ValueError as e:
        if "rejected" in str(e):
            raise
    port = f":{parsed.port}" if parsed.port and parsed.port not in (80, 443) else ""
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme}://{host}{port}{parsed.path or '/'}{query}"


def _normalize_seeds(seeds) -> dict:
    """Validate + normalize all seed inputs. Returns urls/sitemap/shopify/rejected."""
    urls: List[str] = []
    errors: List[str] = []

    for u in seeds.urls or []:
        try:
            urls.append(_normalize_seed(u))
        except ValueError as e:
            errors.append(str(e))

    if seeds.domains_csv:
        for line in seeds.domains_csv.splitlines():
            line = line.strip()
            if not line or line.lower() in ("domain", "url", "website"):
                continue
            try:
                urls.append(_normalize_seed(line.split(",")[0]))
            except ValueError as e:
                errors.append(str(e))

    sitemap = None
    if seeds.sitemap_url:
        try:
            sitemap = _normalize_seed(seeds.sitemap_url)
        except ValueError as e:
            errors.append(str(e))

    shopify = None
    if seeds.shopify_url:
        try:
            shopify = _normalize_seed(seeds.shopify_url)
        except ValueError as e:
            errors.append(str(e))

    seen, deduped = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)

    if not deduped and not sitemap and not shopify:
        msg = "; ".join(errors) if errors else "No seeds provided"
        raise HTTPException(status_code=400, detail=f"Seed stage failed: {msg}")

    return {"urls": deduped, "sitemap": sitemap, "shopify": shopify, "rejected": errors}
# ---------------------------------------------------------------------------
# Credits (6.5 -- documented formula, charged at enqueue like Social Scout):
#   cost = SCRAPLING_CREDIT_BASE
#        + (estimated_pages * SCRAPLING_CREDIT_PER_PAGE)
#        + (enrich_emails ? 0.25 * max_leads : 0)
#        + (generate_outreach ? 0.1 * max_leads : 0)
# Mid-job page overage: pipeline pauses + sets error_msg (never silently continues).
# ---------------------------------------------------------------------------

def compute_credit_cost(brief, enrich_emails: bool, generate_outreach: bool) -> float:
    estimated_pages = max(1, int(brief.max_pages))
    cost = settings.SCRAPLING_CREDIT_BASE
    cost += estimated_pages * settings.SCRAPLING_CREDIT_PER_PAGE
    if enrich_emails:
        cost += 0.25 * brief.max_leads
    if generate_outreach:
        cost += 0.1 * brief.max_leads
    return round(cost, 2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _job_envelope(job: LeadGenJob) -> LeadGenJobEnvelope:
    return LeadGenJobEnvelope(
        job_id=job.id,
        status=job.status,
        stage=job.stage,
        stage_label=job.stage_label,
        stage_index=job.stage_index,
        stages_total=job.stages_total,
        logs=list(job.logs or []),
        leads_count=job.leads_count or 0,
        pages_fetched=job.pages_fetched or 0,
        pages_blocked=job.pages_blocked or 0,
        elapsed_ms=job.elapsed_ms or 0,
        credits_used=job.credits_used or 0.0,
        robots_obey=bool(job.robots_obey),
        engine_default=job.engine_default,
        mode=job.mode,
        recipe_id=job.recipe_id,
        error_msg=job.error_msg,
        created_at=job.created_at.isoformat() if job.created_at else None,
    )


async def _get_owned_job(db: AsyncSession, job_id: str, user: User) -> LeadGenJob:
    job = (await db.execute(
        select(LeadGenJob).where(LeadGenJob.id == job_id)
    )).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Lead Generation job not found")
    if user.role != "admin":
        from app.models.organization import Organization
        my_org = (await db.execute(
            select(Organization.id).where(Organization.owner_id == user.id)
        )).scalar_one_or_none()
        if job.org_id != my_org:
            raise HTTPException(status_code=404, detail="Lead Generation job not found")
    return job


def _is_worker_available() -> bool:
    return bool(settings.SCRAPLING_WORKER_ENABLED or settings.SCRAPLING_INLINE_WORKER)


def _lead_to_dict(l: LeadGenLead) -> dict:
    return {
        "id": l.id,
        "job_id": l.job_id,
        "company_name": l.company_name,
        "website": l.website,
        "domain": l.domain,
        "emails": l.emails or [],
        "phones": l.phones or [],
        "socials": l.socials or {},
        "address": l.address,
        "decision_makers": l.decision_makers or [],
        "markdown_excerpt": l.markdown_excerpt,
        "markdown_artifact_path": l.markdown_artifact_path,
        "extract_status": l.extract_status,
        "fetch_status": l.fetch_status,
        "engine_used": l.engine_used,
        "email_source": l.email_source,
        "phone_source": l.phone_source,
        "lead_score": l.lead_score or 0,
        "priority": l.priority,
        "outreach": l.outreach,
        "sources": l.sources or {},
        "created_at": l.created_at.isoformat() if l.created_at else None,
    }
# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/jobs")
async def create_leadgen_job(
    req: CreateLeadGenJobRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stage 4.1 brief + 4.2 seed validation, credit charge, enqueue."""
    # --- 4.1 Brief validation ---
    brief = req.brief
    if not brief.icp or len(brief.icp.strip()) < 3:
        raise HTTPException(status_code=400, detail="Brief stage failed: icp is required")
    if brief.max_pages < 1 or brief.max_leads < 1:
        raise HTTPException(status_code=400, detail="Brief stage failed: max_pages and max_leads must be >= 1")
    if req.engine_default not in ("http", "stealth", "dynamic"):
        raise HTTPException(status_code=400, detail=f"Unknown engine: {req.engine_default}")
    if req.mode not in ("crawl", "sitemap", "shopify", "csv_feed", "digest"):
        raise HTTPException(status_code=400, detail=f"Unknown mode: {req.mode}")

    # --- 4.2 Seed validation (SSRF / scheme guards) ---
    normalized = _normalize_seeds(req.seeds)

    # --- Worker gate: never queue work nothing will claim ---
    if not _is_worker_available():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "worker_offline",
                "message": "Lead Generation worker is offline. Start the Scrapling worker (SCRAPLING_WORKER_ENABLED=true) and try again.",
            },
        )

    # --- Recipe validation ---
    if req.recipe_id:
        if not any(r["id"] == req.recipe_id for r in _load_recipes()):
            raise HTTPException(status_code=400, detail=f"Unknown recipe: {req.recipe_id}")

    # --- Credits (charged at enqueue; admins bypass) ---
    credit_cost = compute_credit_cost(brief, req.enrich_emails, req.generate_outreach)
    if brief.credit_budget < settings.SCRAPLING_CREDIT_BASE:
        raise HTTPException(status_code=402, detail="credit_budget below minimum base cost")
    org = await get_or_create_default_org(db, current_user)
    is_admin = current_user.role == "admin" or getattr(current_user, "is_superuser", False)
    if not is_admin:
        available = org.credit_balance if org else 0.0
        if available < credit_cost:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Required: {credit_cost:.2f}, Available: {available:.2f}",
            )
        org.credit_balance = max(0.0, available - credit_cost)

    # --- Audit line when robots_obey=false (9. honesty/legal) ---
    logs = [
        f"> brief · icp_ok · geos={len(brief.geos)} · max_pages={brief.max_pages} · max_leads={brief.max_leads}",
        f"> seed · urls={len(normalized['urls'])} · sitemap={'yes' if normalized['sitemap'] else 'no'} · shopify={'yes' if normalized['shopify'] else 'no'}",
    ]
    for rejected in normalized.get("rejected", []):
        logs.append(f"> seed · rejected · {rejected}")
    if not req.robots_obey:
        logs.append(f"> audit · robots_obey=false · user={current_user.id}")

    job = LeadGenJob(
        org_id=org.id,
        user_id=current_user.id,
        status="queued",
        stage="brief",
        stage_label="Job queued",
        stage_index=0,
        stages_total=STAGES_TOTAL,
        brief=brief.model_dump(),
        seeds=normalized,
        engine_default=req.engine_default,
        mode=req.mode,
        recipe_id=req.recipe_id,
        robots_obey=req.robots_obey,
        adaptive=req.adaptive,
        capture_xhr_pattern=req.capture_xhr_pattern,
        enrich_emails=req.enrich_emails,
        generate_outreach=req.generate_outreach,
        proxy_mode=req.proxy_mode,
        logs=logs,
        credits_used=credit_cost if not is_admin else 0.0,
        credit_budget=credit_cost,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # --- Enqueue: inline fallback (dev) or leave queued for the Docker worker ---
    if settings.SCRAPLING_INLINE_WORKER and not settings.SCRAPLING_WORKER_ENABLED:
        import asyncio
        from app.services.leadgen_pipeline import run_leadgen_job  # lazy: no browsers at boot
        asyncio.create_task(run_leadgen_job(job.id))

    return _job_envelope(job)


@router.get("/jobs/{job_id}", response_model=LeadGenJobEnvelope)
async def get_leadgen_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await _get_owned_job(db, job_id, current_user)
    return _job_envelope(job)


@router.get("/jobs/{job_id}/leads")
async def list_leadgen_leads(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await _get_owned_job(db, job_id, current_user)
    result = await db.execute(
        select(LeadGenLead)
        .where(LeadGenLead.job_id == job.id)
        .order_by(desc(LeadGenLead.lead_score), desc(LeadGenLead.created_at))
    )
    leads = result.scalars().all()
    return {"items": [_lead_to_dict(l) for l in leads], "total": len(leads)}


@router.get("/jobs/{job_id}/leads/{lead_id}")
async def get_leadgen_lead(
    job_id: str,
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_job(db, job_id, current_user)
    lead = (await db.execute(
        select(LeadGenLead).where(LeadGenLead.id == lead_id, LeadGenLead.job_id == job_id)
    )).scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _lead_to_dict(lead)
@router.post("/jobs/{job_id}/pause")
async def pause_leadgen_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await _get_owned_job(db, job_id, current_user)
    if job.status not in ("queued", "running"):
        raise HTTPException(status_code=409, detail=f"Cannot pause a {job.status} job")
    job.status = "paused"
    job.stage_label = "Paused by operator"
    job.logs = list(job.logs or []) + ["> pause · checkpoint requested · waiting for worker"]
    await db.commit()
    return _job_envelope(job)


@router.post("/jobs/{job_id}/resume")
async def resume_leadgen_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await _get_owned_job(db, job_id, current_user)
    if job.status != "paused":
        raise HTTPException(status_code=409, detail=f"Cannot resume a {job.status} job")
    job.status = "queued"
    job.stage_label = "Resumed - waiting for worker"
    job.logs = list(job.logs or []) + [
        f"> resume · from checkpoint={'yes' if job.checkpoint_path else 'no'}"
    ]
    await db.commit()
    if settings.SCRAPLING_INLINE_WORKER and not settings.SCRAPLING_WORKER_ENABLED:
        import asyncio
        from app.services.leadgen_pipeline import run_leadgen_job
        asyncio.create_task(run_leadgen_job(job.id))
    return _job_envelope(job)


_EXPORT_COLUMNS = [
    "id", "company_name", "website", "domain", "emails", "phones", "socials",
    "address", "email_source", "phone_source", "extract_status", "fetch_status",
    "engine_used", "lead_score", "priority", "decision_makers", "outreach_subject",
    "markdown_artifact_path", "source_urls",
]


def _export_rows(leads: List[LeadGenLead]):
    """Yield dicts with provenance columns - empty stays empty, never fabricated."""
    for l in leads:
        sources = l.sources or {}
        yield {
            "id": l.id,
            "company_name": l.company_name or "",
            "website": l.website or "",
            "domain": l.domain or "",
            "emails": ";".join(l.emails or []),
            "phones": ";".join(l.phones or []),
            "socials": json.dumps(l.socials or {}, ensure_ascii=False),
            "address": l.address or "",
            "email_source": l.email_source or "none",
            "phone_source": l.phone_source or "none",
            "extract_status": l.extract_status or "empty",
            "fetch_status": l.fetch_status or "ok",
            "engine_used": l.engine_used or "",
            "lead_score": l.lead_score or 0,
            "priority": l.priority or "",
            "decision_makers": json.dumps(l.decision_makers or [], ensure_ascii=False),
            "outreach_subject": (l.outreach or {}).get("subject", ""),
            "markdown_artifact_path": l.markdown_artifact_path or "",
            "source_urls": ";".join(sources.get("urls", []) or []),
        }


async def _load_job_leads(db: AsyncSession, job_id: str) -> List[LeadGenLead]:
    result = await db.execute(
        select(LeadGenLead).where(LeadGenLead.job_id == job_id).order_by(desc(LeadGenLead.lead_score))
    )
    return list(result.scalars().all())


@router.get("/jobs/{job_id}/export.csv")
async def export_leadgen_csv(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await _get_owned_job(db, job_id, current_user)
    leads = await _load_job_leads(db, job_id)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_EXPORT_COLUMNS)
    writer.writeheader()
    for row in _export_rows(leads):
        writer.writerow(row)
    # Honest log line; empty leads => headers-only (no fake rows)
    job.logs = list(job.logs or []) + [f"> export · csv · rows={len(leads)}"]
    await db.commit()
    filename = f"helix_leadgen_{job_id[:8]}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/jobs/{job_id}/export.jsonl")
async def export_leadgen_jsonl(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await _get_owned_job(db, job_id, current_user)
    leads = await _load_job_leads(db, job_id)
    lines = "\n".join(json.dumps(row, ensure_ascii=False) for row in _export_rows(leads))
    job.logs = list(job.logs or []) + [f"> export · jsonl · rows={len(leads)}"]
    await db.commit()
    filename = f"helix_leadgen_{job_id[:8]}.jsonl"
    return StreamingResponse(
        iter([lines + ("\n" if lines else "")]),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _load_recipes() -> list:
    """Load recipe JSON files from app/data/leadgen_recipes/ (read fresh each call)."""
    if not RECIPES_DIR.exists():
        return []
    recipes = []
    for path in sorted(RECIPES_DIR.glob("*.json")):
        try:
            recipes.append(json.loads(path.read_text(encoding="utf-8-sig")))
        except Exception as e:
            logger.warning("Skipping invalid recipe %s: %s", path.name, e)
    return recipes


@router.get("/recipes")
async def list_recipes(current_user: User = Depends(get_current_user)):
    items = _load_recipes()
    return {"items": items, "total": len(items)}
@router.get("/worker/health")
async def worker_health(db: AsyncSession = Depends(get_db)):
    """Truthful worker health - online only when a fresh heartbeat exists
    (or the optional worker URL answers). Offline => UI shows honest empty/error."""
    proxy = "configured" if settings.SCRAPLING_PROXY_LIST.strip() else "off"
    payload = {
        "worker": "offline",
        "scrapling_version": None,
        "engines": ["http", "stealth", "dynamic"],
        "browsers_ready": False,
        "proxy": proxy,
        "robots_default": bool(settings.SCRAPLING_ROBOTS_OBEY),
        "engine_default": settings.SCRAPLING_DEFAULT_ENGINE,
        "queue_depth": 0,
    }

    # Queue depth is always truthful (from the DB), even when offline.
    try:
        payload["queue_depth"] = (await db.execute(
            select(func.count()).select_from(LeadGenJob).where(LeadGenJob.status == "queued")
        )).scalar() or 0
    except Exception:
        pass

    # Optional direct ping (SCRAPLING_WORKER_URL)
    if settings.SCRAPLING_WORKER_URL:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(settings.SCRAPLING_WORKER_URL.rstrip("/") + "/health")
                if r.status_code == 200:
                    data = r.json() if "json" in r.headers.get("content-type", "") else {}
                    payload.update({
                        "worker": "online",
                        "scrapling_version": data.get("version"),
                        "browsers_ready": bool(data.get("browsers_ready", False)),
                        "engines": data.get("engines", payload["engines"]),
                    })
                    return payload
        except Exception:
            pass  # fall through to heartbeat

    # Heartbeat-based check (worker upserts its row every ~30s)
    hb = (await db.execute(
        select(LeadGenWorkerHeartbeat).where(LeadGenWorkerHeartbeat.id == "scrapling_worker")
    )).scalar_one_or_none()
    if hb and hb.updated_at:
        updated = hb.updated_at
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        age_s = (datetime.now(timezone.utc) - updated).total_seconds()
        if age_s <= settings.SCRAPLING_HEARTBEAT_FRESH_S:
            payload.update({
                "worker": "online",
                "scrapling_version": hb.scrapling_version,
                "browsers_ready": bool(hb.browsers_ready),
                "engines": hb.engines or payload["engines"],
                "proxy": hb.proxy_mode or proxy,
            })

    # Inline dev worker counts as online when enabled (it runs in-API).
    if settings.SCRAPLING_INLINE_WORKER and payload["worker"] == "offline":
        payload["worker"] = "online"
        payload["browsers_ready"] = True  # inline implies Scrapling is importable

    return payload


def _worker_expected_token() -> str:
    import hashlib as _hashlib
    return _hashlib.sha256(((settings.SECRET_KEY or "") + "leadgen-worker").encode("utf-8")).hexdigest()


@router.post("/worker/heartbeat")
async def worker_heartbeat(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    x_worker_token: Optional[str] = Header(None, alias="X-Worker-Token"),
):
    """Internal: Scrapling worker registers liveness + engine details.
    Guarded - only accepted when the worker feature is enabled and the token
    matches the derived shared secret (first-party workers only)."""
    if not settings.SCRAPLING_WORKER_ENABLED:
        raise HTTPException(status_code=404, detail="Worker feature disabled")
    import hmac as _hmac
    if not x_worker_token or not _hmac.compare_digest(x_worker_token, _worker_expected_token()):
        raise HTTPException(status_code=401, detail="Invalid worker token")

    hb = (await db.execute(
        select(LeadGenWorkerHeartbeat).where(LeadGenWorkerHeartbeat.id == "scrapling_worker")
    )).scalar_one_or_none()
    if not hb:
        hb = LeadGenWorkerHeartbeat(id="scrapling_worker")
        db.add(hb)
    hb.scrapling_version = payload.get("version")
    hb.engines = payload.get("engines", ["http", "stealth", "dynamic"])
    hb.browsers_ready = bool(payload.get("browsers_ready", False))
    hb.proxy_mode = payload.get("proxy", "off")
    hb.boot_id = payload.get("boot_id")
    hb.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}
