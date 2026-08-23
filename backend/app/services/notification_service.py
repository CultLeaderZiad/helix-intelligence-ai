from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from app.models.notification import Notification
from app.models.user import User

async def create_notification(
    db: AsyncSession,
    user_id: str,
    title: str,
    message: str,
    org_id: Optional[str] = None,
    type: str = "info",
    link: Optional[str] = None
) -> Notification:
    notif = Notification(
        user_id=user_id,
        org_id=org_id,
        type=type,
        title=title,
        message=message,
        link=link,
        is_read=False
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif

async def list_notifications(
    db: AsyncSession,
    user_id: str,
    unread_only: bool = False
) -> Dict[str, Any]:
    query = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        query = query.where(Notification.is_read == False)
    query = query.order_by(desc(Notification.created_at)).limit(30)

    result = await db.execute(query)
    items = result.scalars().all()

    # Total unread count
    unread_count = await db.scalar(
        select(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)
    )

    return {
        "items": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "link": n.link,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() + "Z" if n.created_at else ""
            }
            for n in items
        ],
        "unread_count": sum(1 for n in items if not n.is_read)
    }

async def mark_as_read(db: AsyncSession, user_id: str, notification_id: str) -> Dict[str, Any]:
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user_id)
        .values(is_read=True)
    )
    await db.commit()
    return {"success": True, "message": "Notification marked as read"}

async def mark_all_as_read(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return {"success": True, "message": "All notifications marked as read"}
