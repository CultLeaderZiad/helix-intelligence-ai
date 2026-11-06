"""Board share links (owner side) and the guest read (no sign-in)."""
from typing import Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_feature
from app.models.user import User
from app.services import board_share_service

router = APIRouter(dependencies=[Depends(require_feature("swipe_files"))])
guest_router = APIRouter()


class ShareLinkCreate(BaseModel):
    collection: str = Field(min_length=1, max_length=200)
    expires_in_days: int = 7


@router.get("")
async def list_boards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"items": await board_share_service.list_boards(db, current_user)}


@router.post("/share-links")
async def create_share_link(
    body: ShareLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await board_share_service.create_link(db, current_user, body.collection, body.expires_in_days)


@router.get("/share-links")
async def list_share_links(
    collection: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"items": await board_share_service.list_links(db, current_user, collection)}


@router.delete("/share-links/{link_id}")
async def revoke_share_link(
    link_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await board_share_service.revoke_link(db, current_user, link_id)


@guest_router.get("/{token}")
async def read_guest_board(token: str, response: Response, db: AsyncSession = Depends(get_db)):
    board = await board_share_service.read_guest_board(db, token)
    # A capability URL: never cache it, never index it, never leak it onward.
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Referrer-Policy"] = "no-referrer"
    return board
