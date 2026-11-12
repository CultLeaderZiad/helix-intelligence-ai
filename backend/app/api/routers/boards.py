"""Board share links (owner side) and the guest read (no sign-in)."""
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response
from app.core import markdown
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import account_rate_limit, get_current_user, get_db, require_feature
from app.models.user import User
from app.services import board_share_service, team_board_service

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


@router.get("/items")
async def get_my_board(
    collection: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """One of the caller's own boards (JSON, or Markdown for agents)."""
    collection, as_md = markdown.split_md(collection)
    board = await team_board_service.get_team_board(db, current_user, current_user.id, collection)
    if markdown.wants_markdown(request, as_md):
        return markdown.response(markdown.ads_document(f"Board: {board['board']}", board["items"]))
    return board


@router.post("/share-links", dependencies=[Depends(account_rate_limit("account-write", "ACCOUNT_WRITE_LIMIT", "ACCOUNT_WRITE_WINDOW_S"))])
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


# Team boards: readable by every current member, only with `team_accounts`.
_team = [Depends(require_feature("team_accounts"))]


@router.get("/team", dependencies=_team)
async def list_team_boards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"items": await team_board_service.list_team_boards(db, current_user)}


@router.get("/team/items", dependencies=_team)
async def get_team_board(
    owner_id: str,
    collection: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await team_board_service.get_team_board(db, current_user, owner_id, collection)


@guest_router.get("/{token}")
async def read_guest_board(token: str, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token, as_md = markdown.split_md(token)
    board = await board_share_service.read_guest_board(db, token)
    if markdown.wants_markdown(request, as_md):
        md = markdown.response(markdown.ads_document(
            f"Board: {board['board']}", board["items"], meta=[f"Read-only guest link · expires {board['expires_at']}"]
        ))
        md.headers["Cache-Control"] = "no-store"
        md.headers["X-Robots-Tag"] = "noindex, nofollow"
        return md
    # A capability URL: never cache it, never index it, never leak it onward.
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Referrer-Policy"] = "no-referrer"
    return board
