from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Request
from app.core import markdown
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.discover import SearchParams, Job
from app.schemas.creative import CreativeResults
from app.schemas.common import Paginated
from app.services import discover_service, creative_service
from app.core.deps import account_rate_limit, get_db, get_current_user, require_feature
from app.models.user import User

router = APIRouter(dependencies=[Depends(require_feature("discover"))])

@router.post(
    "/jobs",
    response_model=Job,
    dependencies=[Depends(account_rate_limit("account-search", "ACCOUNT_SEARCH_LIMIT", "ACCOUNT_SEARCH_WINDOW_S"))],
)
async def search(
    params: SearchParams, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    if not params.query or not params.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    return await discover_service.trigger_search(db, params, current_user.id, background_tasks)

@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.core.tenancy import get_user_org_ids
    scope = await get_user_org_ids(db, current_user)
    return await discover_service.get_job_status(db, job_id, user_org_ids=scope)

@router.post("/jobs/{job_id}/cancel", response_model=Job)
async def cancel_job(job_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.core.tenancy import get_user_org_ids
    scope = await get_user_org_ids(db, current_user)
    return await discover_service.cancel_search(db, job_id, user_org_ids=scope)

async def _job_results(job_id, page, page_size, sort, min_days, min_score, db, current_user, request, forced_md=False):
    from app.core.tenancy import get_user_org_ids
    scope = await get_user_org_ids(db, current_user)
    results = await creative_service.list_creatives(
        db, job_id=job_id, page=page, page_size=page_size, user_org_ids=scope, sort=sort,
        min_days=min_days, min_score=min_score,
    )
    if markdown.wants_markdown(request, forced_md):
        meta = [f"Search job: {job_id}", f"Sort: {sort}", f"Page {results.page} · {len(results.items)} of {results.total} ads"]
        if min_days:
            meta.append(f"Running for {min_days}+ days ({results.hidden_unknown_run_length or 0} with unknown run length hidden)")
        if min_score:
            meta.append(f"Text rubric {min_score:g}+")
        return markdown.response(markdown.ads_document("Competitor ads", results.items, meta=meta))
    return results


@router.get("/jobs/{job_id}/results", response_model=CreativeResults)
async def get_job_results(
    job_id: str,
    request: Request,
    page: int = 1,
    page_size: int = 20,
    sort: str = creative_service.DEFAULT_CREATIVE_SORT,
    min_days: int = 0,
    min_score: float = 0.0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await _job_results(job_id, page, page_size, sort, min_days, min_score, db, current_user, request)


@router.get("/jobs/{job_id}/results.md", include_in_schema=False)
async def get_job_results_markdown(
    job_id: str,
    request: Request,
    page: int = 1,
    page_size: int = 20,
    sort: str = creative_service.DEFAULT_CREATIVE_SORT,
    min_days: int = 0,
    min_score: float = 0.0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await _job_results(job_id, page, page_size, sort, min_days, min_score, db, current_user, request, True)

@router.get("/stored-results")
async def stored_results(
    query: str,
    request: Request,
    page: int = 1,
    page_size: int = 20,
    sort: str = creative_service.DEFAULT_CREATIVE_SORT,
    min_days: int = 0,
    min_score: float = 0.0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Results of the latest finished search for ``query`` in the caller's workspace.

    Read-only: it never starts a search and never spends credits. 404 when the
    workspace has not run that search yet.
    """
    from sqlalchemy import func, select
    from app.core.tenancy import get_user_org_ids
    from app.models.scrape_job import ScrapeJob

    needle = " ".join((query or "").split()).lower()
    if not needle:
        raise HTTPException(status_code=422, detail="query is required")
    scope = await get_user_org_ids(db, current_user)
    stmt = select(ScrapeJob.id).where(
        func.lower(func.trim(ScrapeJob.query)) == needle, ScrapeJob.status == "succeeded"
    )
    if scope is not None:
        stmt = stmt.where(ScrapeJob.org_id.in_(scope or [""]))
    job_id = (await db.execute(stmt.order_by(ScrapeJob.created_at.desc()).limit(1))).scalar_one_or_none()
    if job_id is None:
        raise HTTPException(status_code=404, detail="No finished search for this query in your workspace. Run it in Helix first.")
    return await _job_results(job_id, page, page_size, sort, min_days, min_score, db, current_user, request)


@router.get("/jobs", response_model=Paginated[Job])
async def list_jobs(
    page: int = 1,
    page_size: int = 8,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await discover_service.list_recent_jobs(db, current_user.id, page, page_size)



# ---------------------------------------------------------------------------
# Saved search drafts: stored per user per workspace so they follow the user
# across browsers and devices.
# ---------------------------------------------------------------------------
from typing import Any, Dict, Optional  # noqa: E402

from pydantic import BaseModel, Field  # noqa: E402

from app.services import search_draft_service  # noqa: E402


class SearchDraftCreate(BaseModel):
    title: str = Field(default="", max_length=200)
    query: str = Field(min_length=1, max_length=500)
    notes: str = Field(default="", max_length=2000)
    filters: Optional[Dict[str, Any]] = None


@router.get("/drafts")
async def list_search_drafts(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {"items": await search_draft_service.list_drafts(db, current_user)}


@router.post("/drafts", status_code=201, dependencies=[Depends(account_rate_limit("account-write", "ACCOUNT_WRITE_LIMIT", "ACCOUNT_WRITE_WINDOW_S"))])
async def save_search_draft(
    body: SearchDraftCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await search_draft_service.save_draft(
        db, current_user, title=body.title, query=body.query, notes=body.notes, filters=body.filters
    )


@router.delete("/drafts/{draft_id}")
async def delete_search_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await search_draft_service.delete_draft(db, current_user, draft_id)
