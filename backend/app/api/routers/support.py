from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, Literal, Optional
import json
from pydantic import BaseModel, Field, field_validator

from app.core.deps import account_rate_limit, get_db, get_current_user
from app.models.user import User
from app.services import support_service

router = APIRouter()

class TicketCreateRequest(BaseModel):
    type: Literal["feedback", "bug", "other"] = "feedback"
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=5000)
    tag: Optional[str] = Field(default=None, max_length=100)
    context_data: Optional[Dict[str, Any]] = None

    @field_validator("context_data")
    @classmethod
    def validate_context_size(cls, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if value is None:
            return value
        try:
            size = len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
            raise ValueError("context_data must be JSON serializable") from exc
        if size > 16 * 1024:
            raise ValueError("context_data exceeds the 16 KB limit")
        return value

class TicketReplyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)

@router.post("/tickets", dependencies=[Depends(account_rate_limit("account-write", "ACCOUNT_WRITE_LIMIT", "ACCOUNT_WRITE_WINDOW_S"))])
async def create_ticket(
    body: TicketCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = await support_service.create_ticket(
        db=db,
        user=current_user,
        ticket_type=body.type,
        subject=body.subject,
        message=body.message,
        tag=body.tag,
        context_data=body.context_data
    )
    return {
        "id": ticket.id,
        "type": ticket.type,
        "subject": ticket.subject,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else ""
    }

@router.get("/tickets")
async def list_tickets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await support_service.list_user_tickets(db, current_user.id)

@router.get("/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await support_service.get_ticket_details(db, ticket_id, current_user)

@router.post("/tickets/{ticket_id}/reply", dependencies=[Depends(account_rate_limit("account-write", "ACCOUNT_WRITE_LIMIT", "ACCOUNT_WRITE_WINDOW_S"))])
async def reply_ticket(
    ticket_id: str,
    body: TicketReplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await support_service.add_reply(db, ticket_id, current_user, body.message)
