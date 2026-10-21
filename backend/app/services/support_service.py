from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from fastapi import HTTPException

from app.models.support_ticket import SupportTicket, SupportTicketReply
from app.models.user import User
from app.models.organization import Organization
from app.models.notification import Notification


def _is_support_staff(user: User) -> bool:
    if user.role == "admin":
        return True
    if user.role != "assistant-admin":
        return False
    permissions = getattr(user, "admin_permissions", None)
    if not isinstance(permissions, dict) or permissions.get("support") is False:
        return False
    sections = permissions.get("sections")
    return permissions.get("support") is True or (
        isinstance(sections, (list, tuple)) and "support" in sections
    )


async def create_ticket(
    db: AsyncSession,
    user: User,
    ticket_type: str,
    subject: str,
    message: str,
    tag: Optional[str] = None,
    context_data: Optional[Dict[str, Any]] = None
) -> SupportTicket:
    # Find user's org
    org = (await db.execute(select(Organization).where(Organization.owner_id == user.id))).scalar_one_or_none()
    org_id = org.id if org else None

    ticket = SupportTicket(
        user_id=user.id,
        org_id=org_id,
        type=ticket_type,
        subject=subject,
        message=message,
        status="open",
        tag=tag,
        context_data=context_data or {}
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    # Generate admin-targeted notification for all admins
    admin_users = (await db.execute(
        select(User).where(User.role.in_(["admin", "assistant-admin"]))
    )).scalars().all()

    for admin in admin_users:
        notif = Notification(
            user_id=admin.id,
            org_id=org_id,
            type="support",
            title=f"New {ticket_type.capitalize()} Ticket: {subject[:40]}",
            message=f"From {user.email}: {message[:120]}...",
            link=f"/admin/support?ticket_id={ticket.id}",
            is_read=False
        )
        db.add(notif)

    await db.commit()
    return ticket

async def list_user_tickets(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(SupportTicket)
        .where(SupportTicket.user_id == user_id)
        .order_by(desc(SupportTicket.created_at))
        .limit(limit)
        .offset(offset)
    )
    tickets = result.scalars().all()
    
    # Batch count replies to eliminate N+1 queries (F37)
    replies_count_map = {}
    if tickets:
        ticket_ids = [t.id for t in tickets]
        reply_counts = await db.execute(
            select(SupportTicketReply.ticket_id, func.count(SupportTicketReply.id))
            .where(SupportTicketReply.ticket_id.in_(ticket_ids))
            .group_by(SupportTicketReply.ticket_id)
        )
        replies_count_map = {row[0]: row[1] for row in reply_counts.all()}

    out = []
    for t in tickets:
        out.append({
            "id": t.id,
            "type": t.type,
            "subject": t.subject,
            "message": t.message,
            "status": t.status,
            "tag": t.tag,
            "replies_count": replies_count_map.get(t.id, 0),
            "context_data": t.context_data or {},
            "created_at": t.created_at.isoformat() if t.created_at else "",
            "updated_at": t.updated_at.isoformat() if t.updated_at else ""
        })
    return out

async def get_ticket_details(db: AsyncSession, ticket_id: str, current_user: User) -> Dict[str, Any]:
    ticket = (await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    is_staff = _is_support_staff(current_user)
    if not is_staff and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this ticket")

    # Fetch user email & author
    author = (await db.execute(select(User).where(User.id == ticket.user_id))).scalar_one_or_none()

    # Fetch replies
    replies_res = await db.execute(
        select(SupportTicketReply)
        .where(SupportTicketReply.ticket_id == ticket_id)
        .order_by(SupportTicketReply.created_at.asc())
    )
    replies = replies_res.scalars().all()

    # Batch fetch sender emails to eliminate N+1 queries (F37)
    users_map = {}
    sender_ids = list({r.user_id for r in replies if r.user_id})
    if sender_ids:
        users_res = await db.execute(select(User).where(User.id.in_(sender_ids)))
        users_map = {u.id: u.email for u in users_res.scalars().all()}

    formatted_replies = []
    for r in replies:
        sender_email = users_map.get(r.user_id, "Unknown")
        formatted_replies.append({
            "id": r.id,
            "ticket_id": r.ticket_id,
            "user_id": r.user_id,
            "user_email": sender_email,
            "message": r.message,
            "is_admin": r.is_admin,
            "created_at": r.created_at.isoformat() if r.created_at else ""
        })

    return {
        "id": ticket.id,
        "user_id": ticket.user_id,
        "user_email": author.email if author else "Unknown",
        "type": ticket.type,
        "subject": ticket.subject,
        "message": ticket.message,
        "status": ticket.status,
        "tag": ticket.tag,
        "context_data": ticket.context_data or {},
        "created_at": ticket.created_at.isoformat() if ticket.created_at else "",
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else "",
        "replies": formatted_replies
    }

async def add_reply(
    db: AsyncSession,
    ticket_id: str,
    user: User,
    message: str
) -> Dict[str, Any]:
    ticket = (await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    is_staff = _is_support_staff(user)
    if not is_staff and ticket.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to reply to this ticket")

    reply = SupportTicketReply(
        ticket_id=ticket.id,
        user_id=user.id,
        message=message,
        is_admin=is_staff
    )
    db.add(reply)

    # If ticket was resolved and user replied, reopen it
    if not is_staff and ticket.status == "resolved":
        ticket.status = "open"
    elif is_staff and ticket.status == "open":
        ticket.status = "in_progress"

    await db.commit()
    await db.refresh(reply)

    # Notify counterpart
    if is_staff:
        # Admin replied -> notify ticket creator
        notif = Notification(
            user_id=ticket.user_id,
            org_id=ticket.org_id,
            type="support_reply",
            title=f"Support Reply: {ticket.subject[:40]}",
            message=f"Helix Support replied: {message[:120]}...",
            link=f"/support?ticket_id={ticket.id}",
            is_read=False
        )
        db.add(notif)
    else:
        # User replied -> notify admins
        admin_users = (await db.execute(
            select(User).where(User.role.in_(["admin", "assistant-admin"]))
        )).scalars().all()
        for admin in admin_users:
            notif = Notification(
                user_id=admin.id,
                org_id=ticket.org_id,
                type="support_reply",
                title=f"User Reply on Ticket: {ticket.subject[:40]}",
                message=f"From {user.email}: {message[:120]}...",
                link=f"/admin/support?ticket_id={ticket.id}",
                is_read=False
            )
            db.add(notif)

    await db.commit()
    return {
        "id": reply.id,
        "ticket_id": reply.ticket_id,
        "user_id": reply.user_id,
        "user_email": user.email,
        "message": reply.message,
        "is_admin": reply.is_admin,
        "created_at": reply.created_at.isoformat() if reply.created_at else ""
    }

async def update_ticket_status(db: AsyncSession, ticket_id: str, new_status: str) -> Dict[str, Any]:
    if new_status not in ["open", "in_progress", "resolved"]:
        raise HTTPException(status_code=400, detail="Invalid status. Choose open, in_progress, or resolved.")

    ticket = (await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = new_status
    await db.commit()
    return {"status": "ok", "ticket_id": ticket_id, "new_status": new_status}

async def list_admin_tickets(
    db: AsyncSession,
    status_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    query = select(SupportTicket).order_by(desc(SupportTicket.created_at))
    if status_filter and status_filter != "all":
        query = query.where(SupportTicket.status == status_filter)
    if type_filter and type_filter != "all":
        query = query.where(SupportTicket.type == type_filter)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    tickets = result.scalars().all()

    # Batch fetch user emails to eliminate N+1 queries (F37)
    users_map = {}
    user_ids = list({t.user_id for t in tickets if t.user_id})
    if user_ids:
        users_res = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_map = {u.id: u.email for u in users_res.scalars().all()}

    out = []
    for t in tickets:
        user_email = users_map.get(t.user_id, "Unknown")
        out.append({
            "id": t.id,
            "user_id": t.user_id,
            "user_email": user_email,
            "type": t.type,
            "subject": t.subject,
            "message": t.message,
            "status": t.status,
            "tag": t.tag,
            "context_data": t.context_data or {},
            "created_at": t.created_at.isoformat() if t.created_at else "",
            "updated_at": t.updated_at.isoformat() if t.updated_at else ""
        })
    return out
