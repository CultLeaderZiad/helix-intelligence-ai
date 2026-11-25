"""Advertiser page and winner signals (database only, no provider cost)."""
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_feature
from app.core.tenancy import get_user_org_ids
from app.models.user import User
from app.services import advertiser_service, competitor_snapshot

router = APIRouter(dependencies=[Depends(require_feature("discover"))])

BrandId = Path(min_length=1, max_length=200)


@router.get("/{brand_id}")
async def advertiser_summary(brand_id: str = BrandId, db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    scope = await get_user_org_ids(db, current_user)
    return await advertiser_service.summary(db, scope, brand_id)


@router.get("/{brand_id}/ads")
async def advertiser_ads(brand_id: str = BrandId, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50),
                         db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    scope = await get_user_org_ids(db, current_user)
    out = await advertiser_service.winners(db, scope, brand_id, page, page_size)
    if out["total"] == 0:
        raise HTTPException(status_code=404, detail="No ads from this advertiser in your workspace yet.")
    return out


@router.get("/{brand_id}/site")
async def advertiser_site(brand_id: str = BrandId, db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    """One public page of the advertiser's own website. Cached a week; 20 lookups per user per day."""
    scope = await get_user_org_ids(db, current_user)
    domain = await advertiser_service.landing_domain(db, scope, brand_id)
    return await competitor_snapshot.snapshot(current_user.id, domain)
