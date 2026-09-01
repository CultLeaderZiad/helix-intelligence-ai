from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.services import support_service

router = APIRouter()

class TicketCreateRequest(BaseModel):
    type: str = "feedback" # 'feedback' | 'bug' | 'other'
    subject: str
    message: str
    tag: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None

class TicketReplyRequest(BaseModel):
    message: str

@router.post("/tickets")
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

@router.post("/tickets/{ticket_id}/reply")
async def reply_ticket(
    ticket_id: str,
    body: TicketReplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await support_service.add_reply(db, ticket_id, current_user, body.message)
