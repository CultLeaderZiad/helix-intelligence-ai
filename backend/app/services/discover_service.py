from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, BackgroundTasks
import datetime
import asyncio
import uuid
import time
import re
import logging
import httpx
from app.core.observability import log_event

from app.schemas.discover import SearchParams, Job

logger = logging.getLogger(__name__)
_active_discovery_tasks = {}


def _concept_key(creative) -> tuple:
    return (
        creative.format,
        (creative.headline or "").lower().strip(),
        (creative.body or "").lower().strip()[:200],
    )


def _ad_identity(creative) -> tuple:
    ad_id = str(getattr(creative, "source_ad_id", "") or "").strip()
    if ad_id:
        return ("id", getattr(creative, "platform", None), ad_id)
    return ("content", *_concept_key(creative), getattr(creative, "media_url", None))


def group_by_concept(records: list) -> tuple:
    """Group ads that share copy instead of dropping them.

    Only true repeats (the same ad id, or with no id the same copy and media)
    are skipped. Different ads with the same copy are an advertiser testing
    media or audiences: all are kept, share a ``concept_id`` in provenance,
    and ``variant_count`` becomes the number of ads in that concept.
    Returns (kept_records, repeats_skipped).
    """
    kept, seen, concepts = [], set(), {}
    repeats = 0
    for creative, score in records:
        identity = _ad_identity(creative)
        if identity in seen:
            repeats += 1
            continue
        seen.add(identity)
        concepts.setdefault(_concept_key(creative), []).append(creative)
        kept.append((creative, score))
    for members in concepts.values():
        concept_id = str(uuid.uuid4())
        for creative in members:
            creative.variant_count = len(members)
            prov = dict(creative.provenance_json or {})
            prov["concept_id"] = concept_id
            creative.provenance_json = prov
    return kept, repeats


def _is_creative_relevant(creative, query: str, entity_profile: Optional[dict] = None) -> bool:
    clean_q = (query or "").lower().strip()
    if not clean_q or len(clean_q) < 3:
        return True

    # 1. Domain-based matching if query is a domain
    if "." in clean_q and " " not in clean_q:
        q_dom = clean_q.split("://")[-1].split("/")[0].replace("www.", "")
        c_dom = (getattr(creative, "landing_domain", "") or "").lower()
        if q_dom in c_dom or c_dom in q_dom:
            return True

    headline = (getattr(creative, "headline", "") or "").lower()
    body = (getattr(creative, "body", "") or "").lower()
    brand_name = (getattr(creative, "brand_name", "") or "").lower()
    landing_domain = (getattr(creative, "landing_domain", "") or "").lower()
    cta = (getattr(creative, "cta", "") or "").lower()

    text_corpus = f"{headline} {body} {brand_name} {landing_domain} {cta}"

    # Categories come only from a profile built for this query (a model call).
    # There is no built-in list of people, clubs, or product keywords.
    if entity_profile and entity_profile.get("disambiguation", {}).get("filtered_categories"):
        for fc in entity_profile["disambiguation"]["filtered_categories"]:
            fc_clean = fc.lower().strip()
            if fc_clean and fc_clean in text_corpus and clean_q not in brand_name:
                return False

    tokens = [t for t in re.findall(r"\w+", clean_q) if len(t) > 2]
    if not tokens:
        return True

    # 3. Exact full query phrase match with word boundary (Highest confidence)
    if re.search(rf"\b{re.escape(clean_q)}\b", text_corpus):
        return True

    # 4. Multi-token queries (2+ words)
    if len(tokens) >= 2:
        # A single trailing token is not enough for a multi-word query.
        # Check if brand name contains all tokens
        brand_matched = sum(1 for t in tokens if re.search(rf"\b{re.escape(t)}\b", brand_name))
        if brand_matched == len(tokens):
            return True

        # Check if headline contains all tokens
        hl_matched = sum(1 for t in tokens if re.search(rf"\b{re.escape(t)}\b", headline))
        if hl_matched == len(tokens):
            return True

        # Check if first two significant tokens appear within close proximity (<= 40 characters)
        proximity_pattern = (
            rf"\b{re.escape(tokens[0])}\b.{{0,40}}\b{re.escape(tokens[1])}\b|"
            rf"\b{re.escape(tokens[1])}\b.{{0,40}}\b{re.escape(tokens[0])}\b"
        )
        if re.search(proximity_pattern, text_corpus, re.DOTALL):
            return True

        return False

    # 5. Single token match: MUST be an exact word-boundary match (not substring!)
    return bool(re.search(rf"\b{re.escape(tokens[0])}\b", text_corpus))


from app.schemas.common import Paginated
from app.models.scrape_job import ScrapeJob
from app.models.work_item import WorkItem
from app.models.organization import Organization
from app.models.user import User
from app.core.config import settings
from app.db.session import async_session_maker
from app.services.query_bounds import pagination_bounds
from app.services.discovery_cache import discovery_cache_identity


def _job_response(job: ScrapeJob) -> Job:
    # Job rows are nullable at the model level; the response schema is not.
    # Coalesce so a legacy/partial row serializes instead of 500ing.
    return Job(
        job_id=job.id,
        query=getattr(job, "query", None),
        status=job.status or "running",
        progress=float(job.progress or 0.0),
        stage=job.stage or "",
        stage_label=job.stage_label or "",
        stage_index=int(job.stage_index or 0),
        stages_total=int(job.stages_total or 0),
        records_found=int(job.record_count or 0),
        elapsed_ms=int(job.elapsed_ms or 0),
        created_at=_isoformat_utc(job.created_at) if job.created_at else "",
        completed_at=_isoformat_utc(job.completed_at) if job.completed_at else None,
        deadline_at=_isoformat_utc(job.deadline_at) if job.deadline_at else None,
        error=job.error_msg,
        failure_kind=job.failure_kind,
        entity_profile=getattr(job, "entity_profile", None),
    )


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
    ESTIMATED_PROVIDER_COSTS
)
from app.services.api_usage_service import (
    check_global_cap_and_log_preflight,
    mark_api_usage_status,
    APILimitExceeded
)
from app.services.job_heartbeat import heartbeat
from app.services.query_translator import translate_search_query
from app.services.entity_intelligence import analyze_entity_intent


def _utcnow() -> datetime.datetime:
    """Timezone-aware UTC.

    These values land in ``timestamptz`` columns. Writing a naive
    ``utcnow()`` left rows whose ``completed_at`` was three hours before their
    ``created_at``, which also breaks any "how long has this been silent"
    comparison the reconciliation sweep needs to make.
    """
    return datetime.datetime.now(datetime.timezone.utc)


def _isoformat_utc(value: datetime.datetime) -> str:
    if value.utcoffset() is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    else:
        value = value.astimezone(datetime.timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


from app.core.state_machines import SCRAPE_JOB

# Kept as a set for callers; the transition table in app.core.state_machines
# is the source of truth.
DISCOVER_TERMINAL_STATUSES = set(SCRAPE_JOB.terminal)


async def _lock_active_discovery_job(
    db,
    job_id: str,
    *,
    work_item_id: Optional[str] = None,
    lease_owner: Optional[str] = None,
    lease_generation: Optional[int] = None,
) -> Optional[ScrapeJob]:
    job = (
        await db.execute(
            select(ScrapeJob).where(ScrapeJob.id == job_id).with_for_update()
        )
    ).scalars().first()
    if job is None or job.status not in ("queued", "running"):
        return None
    if work_item_id is not None:
        item_id = (
            await db.execute(
                select(WorkItem.id).where(
                    WorkItem.id == work_item_id,
                    WorkItem.job_id == job_id,
                    WorkItem.status == "running",
                    WorkItem.lease_owner == lease_owner,
                    WorkItem.attempt_count == lease_generation,
                    WorkItem.lease_until > _utcnow(),
                ).with_for_update()
            )
        ).scalar_one_or_none()
        if item_id is None:
            return None
    return job


async def _discovery_attempt_is_current(
    job_id: str,
    *,
    work_item_id: Optional[str] = None,
    lease_owner: Optional[str] = None,
    lease_generation: Optional[int] = None,
) -> bool:
    async with async_session_maker() as db:
        job = await _lock_active_discovery_job(
            db,
            job_id,
            work_item_id=work_item_id,
            lease_owner=lease_owner,
            lease_generation=lease_generation,
        )
        return job is not None


def _set_discovery_terminal(
    job: ScrapeJob,
    *,
    status: str,
    failure_kind: Optional[str] = None,
    error: Optional[str] = None,
    stage_label: Optional[str] = None,
) -> None:
    SCRAPE_JOB.check(job.status, status)
    job.status = status
    job.stage = status
    job.stage_label = stage_label or error or status.replace("_", " ").title()
    job.failure_kind = failure_kind
    job.error_msg = error
    job.completed_at = _utcnow()
    job.stage_index = job.stages_total or 5
    if status in ("succeeded", "failed"):
        job.progress = 1.0


async def _finalize_discovery_job(
    job_id: str,
    *,
    status: str,
    failure_kind: Optional[str] = None,
    error: Optional[str] = None,
    stage_label: Optional[str] = None,
    work_item_id: Optional[str] = None,
    lease_owner: Optional[str] = None,
    lease_generation: Optional[int] = None,
    refund_reason: Optional[str] = None,
) -> bool:
    if status not in DISCOVER_TERMINAL_STATUSES:
        raise ValueError(f"invalid Discover terminal status: {status}")
    async with async_session_maker() as db:
        job = await _lock_active_discovery_job(
            db,
            job_id,
            work_item_id=work_item_id,
            lease_owner=lease_owner,
            lease_generation=lease_generation,
        )
        if job is None:
            return False
        org_id = job.org_id
        _set_discovery_terminal(
            job,
            status=status,
            failure_kind=failure_kind,
            error=error,
            stage_label=stage_label,
        )
        job.elapsed_ms = max(0, int((_utcnow() - job.created_at).total_seconds() * 1000))
        if work_item_id and status in ("cancelled", "timed_out"):
            item = (
                await db.execute(
                    select(WorkItem).where(WorkItem.id == work_item_id).with_for_update()
                )
            ).scalars().first()
            if item is not None and item.status == "running":
                item.cancel_requested = _utcnow().isoformat()
        await db.commit()
        if refund_reason:
            try:
                await refund(db, org_id, DISCOVER_SEARCH_CREDIT_COST, refund_reason, job_id)
            except Exception as exc:
                log_event(
                    logger,
                    "discover_terminal_refund_failed",
                    error=exc,
                    job_id=job_id,
                    tenant_id=org_id,
                )
        return True


async def cancel_search(
    db: AsyncSession,
    job_id: str,
    *,
    user_org_ids: Optional[List[str]],
) -> Job:
    query = select(ScrapeJob).where(ScrapeJob.id == job_id)
    if user_org_ids is not None:
        if not user_org_ids:
            raise HTTPException(status_code=404, detail="Job not found")
        query = query.where(ScrapeJob.org_id.in_(user_org_ids))
    job = (await db.execute(query.with_for_update())).scalars().first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in DISCOVER_TERMINAL_STATUSES:
        return _job_response(job)

    org_id = job.org_id
    _set_discovery_terminal(
        job,
        status="cancelled",
        failure_kind="cancelled",
        error="The search was cancelled.",
    )
    now = _utcnow()
    items = (
        await db.execute(
            select(WorkItem).where(
                WorkItem.job_id == job_id,
                WorkItem.org_id == org_id,
                WorkItem.status.in_(("queued", "leased", "running")),
            ).with_for_update()
        )
    ).scalars().all()
    for item in items:
        item.cancel_requested = now.isoformat()
        item.updated_at = now
        if item.status == "queued":
            item.status = "canceled"
            item.lease_owner = None
            item.lease_until = None
    await db.commit()

    try:
        await refund(db, org_id, DISCOVER_SEARCH_CREDIT_COST, "cancelled", job_id)
    except Exception as exc:
        log_event(logger, "discover_cancel_refund_failed", error=exc, job_id=job_id, tenant_id=org_id)
    task = _active_discovery_tasks.get(job_id)
    if task is not None and task is not asyncio.current_task() and not task.done():
        task.cancel()
    await db.refresh(job)
    return _job_response(job)

def _discovery_cache_provider_identity() -> str:
    """Describe the configured fallback chain without retaining credentials."""
    from app.services.scraping.ad_library_provider import _apify_allowed
    provider = AdLibraryProvider()
    enabled = {
        "metapi": bool(provider.metapi_provider.metapi_api_key),
        "adyntel": bool(provider.adyntel_provider.adyntel_api_key and provider.adyntel_provider.adyntel_email),
        "meta_official": bool(provider.meta_token),
        "apify": bool(provider.apify_token) and _apify_allowed(),
    }
    chain = ",".join(name for name in DISCOVERY_PROVIDER_CHAIN if enabled.get(name))
    return f"{chain or 'none'};meta_graph={provider.meta_graph_version}"


async def trigger_search(
    db: AsyncSession,
    search_params: SearchParams,
    user_id: str,
    background_tasks: Optional[BackgroundTasks] = None
) -> Job:
    # 1. Fetch user
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    from app.services import provider_budget

    if provider_budget.discover_paused():
        raise HTTPException(
            status_code=503,
            detail={"code": "discover_paused", "message": "Discover is paused. No credit was used; try again later."},
        )

    org = await get_or_create_default_org(db, user)
    org_id = org.id
    clean_query = (search_params.query or "").strip()
    if len(clean_query) > settings.DISCOVER_MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "query_too_long",
                "message": f"Search text is limited to {settings.DISCOVER_MAX_QUERY_LENGTH} characters.",
            },
        )

    # Entitlement and credits are checked before any paid call, including the
    # model call that translates the query. This first check takes no row
    # lock, so the translation does not hold the workspace row.
    await assert_can_spend(
        db,
        user=user,
        required_credits=DISCOVER_SEARCH_CREDIT_COST,
        feature_name="discover",
        lock_row=False,
    )
    scrape_query = await translate_search_query(clean_query, search_params.query_language or "en", org_id=org.id)

    # Entitlement runs again under the row lock before any cached or
    # in-flight result is returned or a charge is made.
    org, _plan = await assert_can_spend(
        db,
        user=user,
        required_credits=DISCOVER_SEARCH_CREDIT_COST,
        feature_name="discover",
        lock_row=True
    )
    org_id = org.id

    # 2. Duplicate-search guards.
    # 2a. Active guard: an identical query is already queued/running in this
    #     org -> return that job, so the second request polls the first
    #     search's result instead of creating (and charging) a duplicate.
    # 2b. 12-hour cache: only reuse a job that actually stored ads. A succeeded
    #     zero-result (Meta Graph with no commercial coverage) must not block
    #     Metapi/Adyntel after keys are added.
    twelve_hours_ago = _utcnow() - datetime.timedelta(hours=12)
    filters = search_params.filters.model_dump() if hasattr(search_params.filters, "model_dump") else (search_params.filters or {})
    cache_identity = discovery_cache_identity(
        query=scrape_query, filters=filters, org_id=org_id,
        provider=_discovery_cache_provider_identity(),
    )
    active_job_result = await db.execute(
        select(ScrapeJob)
        .where(ScrapeJob.org_id == org_id)
        .where(ScrapeJob.cache_identity == cache_identity)
        .where(ScrapeJob.status.in_(("queued", "running")))
        .order_by(ScrapeJob.created_at.desc())
        .limit(1)
    )
    active_job = active_job_result.scalar_one_or_none()
    if active_job:
        return _job_response(active_job)

    duplicate_job_result = await db.execute(
        select(ScrapeJob)
        .where(ScrapeJob.org_id == org_id)
        .where(ScrapeJob.cache_identity == cache_identity)
        .where(ScrapeJob.status == "succeeded")
        .where(ScrapeJob.record_count > 0)
        .where(ScrapeJob.created_at >= twelve_hours_ago)
        .order_by(ScrapeJob.created_at.desc())
        .limit(1)
    )
    duplicate_job = duplicate_job_result.scalar_one_or_none()
    if duplicate_job:
        return _job_response(duplicate_job)

    # 2c. A very recent identical search that found no ads is shown again
    #     instead of calling the provider again (its credit was refunded).
    zero_window = max(0, int(settings.DISCOVER_ZERO_RESULT_CACHE_MINUTES))
    if zero_window:
        recent_empty = (await db.execute(
            select(ScrapeJob)
            .where(ScrapeJob.org_id == org_id)
            .where(ScrapeJob.cache_identity == cache_identity)
            .where(ScrapeJob.status == "succeeded")
            .where(ScrapeJob.record_count == 0)
            .where(ScrapeJob.created_at >= _utcnow() - datetime.timedelta(minutes=zero_window))
            .order_by(ScrapeJob.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        if recent_empty:
            return _job_response(recent_empty)

    # 3. Per-workspace daily search cap. Counted before any provider work and
    #    never lowered by a refund, so refunded searches still count.
    from app.services.provider_budget import RECORD_BUDGET, record_refusal, reserve_search_slot

    # 3a. Monthly Metapi record caps: refuse before any provider work.
    refusal = await record_refusal(db, org_id)
    if refusal:
        platform = refusal == RECORD_BUDGET
        raise HTTPException(
            status_code=429,
            detail={
                "code": "platform_record_budget_reached" if platform else "workspace_record_budget_reached",
                "message": (
                    "Live searches are paused for everyone until the monthly data budget resets on the 1st (UTC). "
                    "Saved searches and past results stay available."
                    if platform else
                    "This workspace has used its live-search data for this month. "
                    "Saved searches and past results stay available. Resets on the 1st (UTC)."
                ),
            },
        )

    if not await reserve_search_slot(org_id):
        raise HTTPException(
            status_code=429,
            detail={
                "code": "daily_search_cap_reached",
                "message": (
                    f"This workspace has started {settings.DISCOVER_MAX_SEARCHES_PER_WORKSPACE_PER_DAY} "
                    "searches today. Saved searches and past results stay available. Resets at 00:00 UTC."
                ),
                "daily_search_cap": settings.DISCOVER_MAX_SEARCHES_PER_WORKSPACE_PER_DAY,
            },
        )

    # 4. Create new ScrapeJob. The partial unique canonical-identity index
    # makes a duplicate active job structurally impossible. Legacy rows have
    # no identity and cannot be safely reused. If a concurrent identical
    # request won the insert race, we roll back and return its job — before
    # any credits are charged.
    from app.services.work_outbox import enqueue_work, inline_execution_enabled
    inline = inline_execution_enabled()
    created_at = _utcnow()
    deadline_at = created_at + datetime.timedelta(
        seconds=max(1, int(settings.DISCOVER_JOB_DEADLINE_S))
    )
    new_job = ScrapeJob(
        org_id=org_id,
        query=scrape_query,
        cache_identity=cache_identity,
        status="running" if inline else "queued",
        created_at=created_at,
        deadline_at=deadline_at,
        progress=0.1 if inline else 0.0,
        stage="init" if inline else "queued",
        stage_label="Initializing Search" if inline else "Queued",
        stage_index=0,
        stages_total=5,
        elapsed_ms=100 if inline else 0,
        record_count=0
    )
    try:
        async with db.begin_nested():
            db.add(new_job)
            await db.flush()
    except IntegrityError:
        winner_result = await db.execute(
            select(ScrapeJob)
            .where(ScrapeJob.org_id == org_id)
            .where(ScrapeJob.cache_identity == cache_identity)
            .where(ScrapeJob.status.in_(("queued", "running", "succeeded")))
            .order_by(ScrapeJob.created_at.desc())
            .limit(1)
        )
        winner = winner_result.scalar_one_or_none()
        winner_created = winner.created_at if winner else None
        if winner_created is not None and winner_created.tzinfo is None:
            winner_created = winner_created.replace(tzinfo=datetime.timezone.utc)
        if winner and (winner.status in ("queued", "running") or (
            winner.status == "succeeded" and (winner.record_count or 0) > 0
            and winner_created and winner_created >= twelve_hours_ago
        )):
            return _job_response(winner)
        raise HTTPException(
            status_code=409,
            detail={
                "code": "duplicate_search",
                "message": "A search for this query is already in progress or was just completed. Please retry in a moment.",
            },
        )

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
        metadata={"query": scrape_query, "original_query": clean_query}
    )

    try:
        await enqueue_work(
            db,
            kind="discover",
            job_id=new_job.id,
            org_id=org_id,
            user_id=user.id,
            payload={"query": scrape_query, "filters": filters},
        )
    except Exception as exc:
        log_event(logger, "discover_enqueue_failed", error=exc, job_id=new_job.id, tenant_id=org.id, actor_id=user_id)
    if inline_execution_enabled():
        if background_tasks:
            background_tasks.add_task(run_discovery_pipeline, new_job.id, scrape_query, search_params.filters)
        else:
            asyncio.create_task(run_discovery_pipeline(new_job.id, scrape_query, search_params.filters))

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
        created_at=_isoformat_utc(new_job.created_at) if new_job.created_at else "",
        deadline_at=_isoformat_utc(new_job.deadline_at) if new_job.deadline_at else None,
    )

async def get_job_status(db: AsyncSession, job_id: str, user_org_ids: Optional[List[str]] = None) -> Job:
    result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Tenant isolation: a cross-tenant job must be indistinguishable from a
    # missing one (404, never 403) so job ids cannot be enumerated.
    if user_org_ids is not None and job.org_id not in user_org_ids:
        raise HTTPException(status_code=404, detail="Job not found")

    now = _utcnow()
    deadline_at = job.deadline_at
    if deadline_at is None and job.created_at is not None:
        deadline_at = job.created_at + datetime.timedelta(
            seconds=max(1, int(settings.DISCOVER_JOB_DEADLINE_S))
        )
    if job.status in ("queued", "running") and deadline_at is not None and deadline_at <= now:
        await _finalize_discovery_job(
            job_id,
            status="timed_out",
            failure_kind="deadline",
            error="The search exceeded its server time limit. Please retry.",
            refund_reason="deadline",
        )
        await db.refresh(job)

    return _job_response(job)

async def list_recent_jobs(db: AsyncSession, user_id: str, page: int = 1, page_size: int = 8) -> Paginated[Job]:
    offset, page_size = pagination_bounds(page, page_size)
    count_query = select(func.count(ScrapeJob.id)).join(
        Organization, ScrapeJob.org_id == Organization.id
    ).where(Organization.owner_id == user_id)
    total = await db.scalar(count_query) or 0

    query = select(ScrapeJob).join(
        Organization, ScrapeJob.org_id == Organization.id
    ).where(Organization.owner_id == user_id).order_by(
        ScrapeJob.created_at.desc(), ScrapeJob.id
    ).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    jobs = result.scalars().all()

    items = [_job_response(job) for job in jobs]

    return Paginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total
    )

async def update_job_stage(
    db: AsyncSession,
    job_id: str,
    stage: str,
    label: str,
    progress: float,
    stage_index: int,
    *,
    work_item_id: Optional[str] = None,
    lease_owner: Optional[str] = None,
    lease_generation: Optional[int] = None,
) -> bool:
    job = await _lock_active_discovery_job(
        db,
        job_id,
        work_item_id=work_item_id,
        lease_owner=lease_owner,
        lease_generation=lease_generation,
    )
    if job is None:
        return False
    job.stage = stage
    job.stage_label = label
    job.progress = progress
    job.stage_index = stage_index
    await db.commit()
    return True


async def refund_zero_result_search(db: AsyncSession, org_id: str, job_id: str) -> bool:
    """Refund a Discover search that finished with no ads for the user.

    Only the search's own ``discover_job_start`` charge is refunded (never a
    monitor run or pattern scoring), once per job. Per-workspace and global
    provider counters, rate limits and attempt counts are not touched.
    """
    try:
        refunded = await refund(
            db, org_id, DISCOVER_SEARCH_CREDIT_COST, "no_results", job_id,
            only_operation="discover_job_start",
        )
    except Exception as exc:
        log_event(logger, "discover_zero_result_refund_failed", error=exc, job_id=job_id, tenant_id=org_id)
        return False
    if refunded:
        log_event(logger, "discover_zero_result_refunded", job_id=job_id, tenant_id=org_id, level=logging.INFO)
    return refunded


async def run_discovery_pipeline(
    job_id: str,
    query: str,
    filters: dict = None,
    *,
    work_item_id: Optional[str] = None,
    lease_owner: Optional[str] = None,
    lease_generation: Optional[int] = None,
):
    """Claim the job for this process, then run it.

    The heartbeat is what lets a restart distinguish this job from an
    abandoned one; see job_reconciliation.
    """
    async with async_session_maker() as db:
        job = await _lock_active_discovery_job(
            db,
            job_id,
            work_item_id=work_item_id,
            lease_owner=lease_owner,
            lease_generation=lease_generation,
        )
        if job is None:
            return
        deadline_at = job.deadline_at
        if deadline_at is None:
            created_at = job.created_at or _utcnow()
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=datetime.timezone.utc)
            deadline_at = created_at + datetime.timedelta(
                seconds=max(1, int(settings.DISCOVER_JOB_DEADLINE_S))
            )
        elif deadline_at.tzinfo is None:
            deadline_at = deadline_at.replace(tzinfo=datetime.timezone.utc)
        remaining_s = (deadline_at - _utcnow()).total_seconds()

    if remaining_s <= 0:
        await _finalize_discovery_job(
            job_id,
            status="timed_out",
            failure_kind="deadline",
            error="The search exceeded its server time limit. Please retry.",
            work_item_id=work_item_id,
            lease_owner=lease_owner,
            lease_generation=lease_generation,
            refund_reason="deadline",
        )
        return

    task = asyncio.current_task()
    _active_discovery_tasks[job_id] = task
    try:
        async with heartbeat(
            "scrape_jobs",
            job_id,
            work_item_id=work_item_id,
            lease_owner=lease_owner,
            lease_generation=lease_generation,
        ):
            try:
                await asyncio.wait_for(
                    _run_discovery_pipeline(
                        job_id,
                        query,
                        filters,
                        work_item_id=work_item_id,
                        lease_owner=lease_owner,
                        lease_generation=lease_generation,
                    ),
                    timeout=remaining_s,
                )
            except httpx.TimeoutException:
                await _finalize_discovery_job(
                    job_id, status="failed", failure_kind="provider_timeout",
                    error="A discovery provider timed out. Please retry.",
                    work_item_id=work_item_id, lease_owner=lease_owner,
                    lease_generation=lease_generation, refund_reason="provider_timeout",
                )
            except TimeoutError:
                await _finalize_discovery_job(
                    job_id,
                    status="timed_out",
                    failure_kind="deadline",
                    error="The search exceeded its server time limit. Please retry.",
                    work_item_id=work_item_id,
                    lease_owner=lease_owner,
                    lease_generation=lease_generation,
                    refund_reason="deadline",
                )
    finally:
        if _active_discovery_tasks.get(job_id) is task:
            _active_discovery_tasks.pop(job_id, None)


async def _run_discovery_pipeline(
    job_id: str,
    query: str,
    filters: dict = None,
    *,
    work_item_id: Optional[str] = None,
    lease_owner: Optional[str] = None,
    lease_generation: Optional[int] = None,
):
    query = (query or "").strip()
    start_time = time.time()
    async with async_session_maker() as db:
        job = await _lock_active_discovery_job(
            db,
            job_id,
            work_item_id=work_item_id,
            lease_owner=lease_owner,
            lease_generation=lease_generation,
        )
        if not job:
            return
        org_id = job.org_id
        org_row = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
        owner = None
        if org_row is not None:
            owner = (await db.execute(select(User).where(User.id == org_row.owner_id))).scalar_one_or_none()
        if owner is not None:
            from app.services.billing_service import assert_can_spend as _recheck
            try:
                await _recheck(db, owner, required_credits=0.0, feature_name="discover", lock_row=False)
            except HTTPException:
                await db.rollback()
                await _finalize_discovery_job(
                    job_id,
                    status="failed",
                    failure_kind="entitlement",
                    error="Workspace is not entitled to run this search.",
                    work_item_id=work_item_id,
                    lease_owner=lease_owner,
                    lease_generation=lease_generation,
                    refund_reason="entitlement",
                )
                return
        job.status = "running"
        job.stage = "init"
        job.stage_label = "Initializing Search"
        await db.commit()
        
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

        # A model dossier is kept. The no-key heuristic invents a strategy for
        # every query, so it is not stored or shown.
        entity_profile = await analyze_entity_intent(query)
        if not entity_profile or entity_profile.get("evidence_status") == "unverified_heuristic":
            entity_profile = None

        # Stage 1: Canonical Ad Library Scraper Chain
        async with async_session_maker() as db:
            active = await update_job_stage(
                db, job_id, "scraping", "Scraping Platforms", 0.2, 1,
                work_item_id=work_item_id,
                lease_owner=lease_owner,
                lease_generation=lease_generation,
            )
        if not active:
            return
        
        async def on_scraping_progress(elapsed_s: int, msg: str):
            async with async_session_maker() as db:
                j = await _lock_active_discovery_job(
                    db,
                    job_id,
                    work_item_id=work_item_id,
                    lease_owner=lease_owner,
                    lease_generation=lease_generation,
                )
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
        if not await _discovery_attempt_is_current(
            job_id,
            work_item_id=work_item_id,
            lease_owner=lease_owner,
            lease_generation=lease_generation,
        ):
            return
        sources_tried = ad_lib_provider.sources_tried
        # Ads loaded by advertiser (the brand's own page) are relevant by
        # definition; the keyword relevance filter is for keyword results.
        metapi = getattr(ad_lib_provider, "metapi_provider", None)
        advertiser_mode = (
            getattr(ad_lib_provider, "last_provider_used", "") == "metapi"
            and getattr(metapi, "last_mode", "") == "advertiser"
        )
        advertiser_label = getattr(metapi, "resolved_page_name", None) if advertiser_mode else None

        # Global hard stop: the kill switch or the daily provider cap refused a
        # paid call. Not retried (retrying would only be refused again); the
        # search credit is refunded.
        stopped = getattr(ad_lib_provider, "stopped_reason", None)
        if stopped and not raw_creatives:
            paused = stopped == "paused"
            await _finalize_discovery_job(
                job_id,
                status="failed",
                failure_kind="discover_paused" if paused else "provider_budget",
                error=(
                    "Discover is paused by the operator. Your credit was refunded."
                    if paused
                    else "Today's search capacity is used up. Your credit was refunded; try again tomorrow."
                ),
                stage_label="Paused" if paused else "Daily capacity reached",
                work_item_id=work_item_id,
                lease_owner=lease_owner,
                lease_generation=lease_generation,
                refund_reason="discover_paused" if paused else "provider_budget",
            )
            if usage_log_id:
                async with async_session_maker() as db:
                    await mark_api_usage_status(db, usage_log_id, "failed")
            return

        # Zero Results vs Provider Outage Handling (F29)
        if not raw_creatives:
            if getattr(ad_lib_provider, "provider_outage", False):
                from app.services.work_outbox import retries_remaining
                from app.services.ai.call_policy import RetryableProviderError
                will_retry = await retries_remaining(job_id)
                sources_str = ", ".join(sources_tried) if sources_tried else "all providers"
                failure_message = (
                    "All ad discovery providers are temporarily unavailable or unconfigured: "
                    f"[{sources_str}]"
                )
                if will_retry:
                    async with async_session_maker() as db:
                        job = await _lock_active_discovery_job(
                            db,
                            job_id,
                            work_item_id=work_item_id,
                            lease_owner=lease_owner,
                            lease_generation=lease_generation,
                        )
                        if job is None:
                            return
                        job.status = SCRAPE_JOB.check(job.status, "queued")
                        job.failure_kind = None
                        job.error_msg = None
                        job.stage = "queued"
                        job.stage_label = "Provider unavailable, retry scheduled"
                        job.elapsed_ms = int((time.time() - start_time) * 1000)
                        await db.commit()
                    if usage_log_id:
                        async with async_session_maker() as db:
                            await mark_api_usage_status(db, usage_log_id, "failed")
                    raise RetryableProviderError("provider_outage")

                await _finalize_discovery_job(
                    job_id,
                    status="failed",
                    failure_kind="provider_outage",
                    error=failure_message,
                    stage_label="Provider Outage",
                    work_item_id=work_item_id,
                    lease_owner=lease_owner,
                    lease_generation=lease_generation,
                    refund_reason="provider_outage",
                )
                if usage_log_id:
                    async with async_session_maker() as db:
                        await mark_api_usage_status(db, usage_log_id, "failed")
                return

            async with async_session_maker() as db:
                job = await _lock_active_discovery_job(
                    db,
                    job_id,
                    work_item_id=work_item_id,
                    lease_owner=lease_owner,
                    lease_generation=lease_generation,
                )
                if job:
                    sources_str = ", ".join(sources_tried) if sources_tried else "available sources"
                    job.entity_profile = entity_profile
                    if entity_profile and entity_profile.get("entity_type") == "creator_streamer":
                        label = (
                            f"'{query}' is recognized as a {entity_profile.get('category_label', 'Content Creator')}. "
                            f"Content creators grow via livestreams, clipping, and sponsors rather than direct Meta feed ads. See Entity Dossier."
                        )
                    else:
                        label = f"No active ads found across [{sources_str}] for '{query}'. Try the company domain or a broader keyword, then run the search again."
                    _set_discovery_terminal(job, status="succeeded", stage_label=label)
                    job.stage = "zero_results"
                    job.record_count = 0
                    job.elapsed_ms = int((time.time() - start_time) * 1000)
                    await db.commit()
                    await refund_zero_result_search(db, org_id, job_id)
            return
            
        # Stage 2: Enriching with ScrapeGraph (Capped at top 2 landing pages)
        async with async_session_maker() as db:
            active = await update_job_stage(
                db, job_id, "enriching", "Enriching via Landing Pages", 0.4, 2,
                work_item_id=work_item_id,
                lease_owner=lease_owner,
                lease_generation=lease_generation,
            )
        if not active:
            return
            
        scrapegraph = ScrapeGraphProvider()
        enriched_creatives = []
        scrapegraph_calls = 0
        for rc in raw_creatives:
            if rc.landing_url and scrapegraph_calls < 2:
                extra_data = await scrapegraph.extract_landing_page(rc.landing_url)
                if not isinstance(extra_data, dict) or extra_data.get("status") in ("failure", "skipped", "empty"):
                    extra_data = None
                enriched_creatives.append((rc, extra_data))
                scrapegraph_calls += 1
            else:
                enriched_creatives.append((rc, None))

        if not await _discovery_attempt_is_current(
            job_id,
            work_item_id=work_item_id,
            lease_owner=lease_owner,
            lease_generation=lease_generation,
        ):
            return
                
        # Stage 3: Normalizing and Saving to DB
        async with async_session_maker() as db:
            active = await update_job_stage(
                db, job_id, "normalizing", "Normalizing & Saving", 0.6, 3,
                work_item_id=work_item_id,
                lease_owner=lease_owner,
                lease_generation=lease_generation,
            )
            if not active:
                return
            job = await _lock_active_discovery_job(
                db,
                job_id,
                work_item_id=work_item_id,
                lease_owner=lease_owner,
                lease_generation=lease_generation,
            )
            if job is None:
                return
            brand_id = str(uuid.uuid4())
            brand_label = advertiser_label or " ".join(w.capitalize() for w in query.split())
            saved_creatives = 0
            rejected_templates = 0
            duplicates_skipped = 0
            rejected_irrelevant = 0
            normalized_records = []

            for rc, extra in enriched_creatives:
                normalized = normalize_creative(rc, job_id, brand_id, extra, brand_label=brand_label)
                if normalized is None:
                    # Pure template macros — not a real creative.
                    rejected_templates += 1
                    continue
                db_creative, db_score = normalized
                normalized_records.append((db_creative, db_score))

            # Drop rows that do not match the caller's query. A model profile may also name categories to exclude.
            relevant_records = (
                list(normalized_records)
                if advertiser_mode
                else [(c, s) for c, s in normalized_records if _is_creative_relevant(c, query, entity_profile)]
            )
            rejected_irrelevant = len(normalized_records) - len(relevant_records)
            # Strictly save genuine relevant records — never force noise back into the user view
            final_records = relevant_records

            final_records, duplicates_skipped = group_by_concept(final_records)
            for db_creative, db_score in final_records:
                db.add(db_creative)
                db.add(db_score)
                saved_creatives += 1

            if rejected_templates or duplicates_skipped or rejected_irrelevant:
                log_event(logger, "discover_records_filtered", job_id=job_id, tenant_id=org_id, level=logging.INFO)
                # Counts only, no ad content: why a search that found ads shows fewer (or none).
                logger.info(
                    "discover filter counts job=%s provider_rows=%d templates=%d irrelevant=%d duplicates=%d saved=%d",
                    job_id, len(enriched_creatives), rejected_templates, rejected_irrelevant, duplicates_skipped, saved_creatives,
                )
            await db.commit()
            
        # Stage 4: AI Pattern Scoring/Generation (Graceful Degradation)
        async with async_session_maker() as db:
            active = await update_job_stage(
                db, job_id, "scoring", "AI Generating Insights", 0.8, 4,
                work_item_id=work_item_id,
                lease_owner=lease_owner,
                lease_generation=lease_generation,
            )
            if not active:
                return
            if not await _discovery_attempt_is_current(
                job_id,
                work_item_id=work_item_id,
                lease_owner=lease_owner,
                lease_generation=lease_generation,
            ):
                return
            org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one()
            user = (await db.execute(select(User).where(User.id == org.owner_id))).scalar_one()
            try:
                await generate_patterns_for_recent_creatives(db, user, job_id)
            except HTTPException as he:
                # If trial expired or plan restricted, gracefully preserve the scraped creatives
                log_event(logger, "discover_pattern_scoring_unavailable", error=he, job_id=job_id, tenant_id=org_id, actor_id=user.id)
            except Exception as ai_err:
                log_event(logger, "discover_pattern_scoring_failed", error=ai_err, job_id=job_id, tenant_id=org_id, actor_id=user.id)
            
        # Stage 5: Complete
        async with async_session_maker() as db:
            job = await _lock_active_discovery_job(
                db,
                job_id,
                work_item_id=work_item_id,
                lease_owner=lease_owner,
                lease_generation=lease_generation,
            )
            completed = job is not None
            if job:
                job.entity_profile = entity_profile
                if saved_creatives == 0:
                    if entity_profile and entity_profile.get("entity_type") == "creator_streamer":
                        disambig = entity_profile.get("disambiguation", {})
                        confused = disambig.get("confused_with", "shoe stores")
                        label = (
                            f"'{query}' is recognized as a {entity_profile.get('category_label', 'Content Creator')}. "
                            f"Pruned {rejected_irrelevant} off-topic phonetic {confused} matches. See Entity Dossier."
                        )
                    else:
                        label = f"Pruned {rejected_irrelevant} off-topic records for '{query}'. No direct ads verified."
                else:
                    label = "Complete"
                _set_discovery_terminal(job, status="succeeded", stage_label=label)
                job.stage = "complete"
                job.record_count = saved_creatives
                job.elapsed_ms = int((time.time() - start_time) * 1000)
                await db.commit()
                if not saved_creatives:
                    await refund_zero_result_search(db, org_id, job_id)
                if saved_creatives and settings.ARCHIVE_ENABLED:
                    # Permanent copy runs as its own work item so media
                    # downloads never hold up the search result.
                    try:
                        from app.services.work_outbox import enqueue_work
                        await enqueue_work(db, kind="archive", job_id=job_id, org_id=org_id,
                                           idempotency_key=f"archive:{job_id}")
                    except Exception as archive_err:
                        log_event(logger, "discover_archive_enqueue_failed", error=archive_err,
                                  job_id=job_id, tenant_id=org_id)
            
            if usage_log_id:
                await mark_api_usage_status(db, usage_log_id, "success" if completed else "failed")
                
    except APILimitExceeded as e:
        error_msg = "Discovery is temporarily unavailable because provider capacity is exhausted."
        log_event(logger, "discover_capacity_blocked", error=e, job_id=job_id, tenant_id=org_id)
        await _finalize_discovery_job(
            job_id,
            status="failed",
            failure_kind="error",
            error=error_msg,
            work_item_id=work_item_id,
            lease_owner=lease_owner,
            lease_generation=lease_generation,
            refund_reason="api_limit_preflight",
        )
        if usage_log_id:
            async with async_session_maker() as db:
                await mark_api_usage_status(db, usage_log_id, "failed")
    except Exception as e:
        from app.services.ai.call_policy import RetryableProviderError
        if isinstance(e, RetryableProviderError):
            raise
        log_event(logger, "discover_pipeline_failed", error=e, job_id=job_id, tenant_id=org_id)
        await _finalize_discovery_job(
            job_id,
            status="failed",
            failure_kind="error",
            error="Discovery could not be completed. Please retry.",
            work_item_id=work_item_id,
            lease_owner=lease_owner,
            lease_generation=lease_generation,
        )
        async with async_session_maker() as db:
            if usage_log_id:
                await mark_api_usage_status(db, usage_log_id, "failed")
