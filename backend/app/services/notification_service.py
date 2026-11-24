from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from app.models.notification import Notification

async def create_notification(
    db: AsyncSession,
    user_id: str,
    title: str,
    message: str,
    org_id: Optional[str] = None,
    type: str = "info",
    link: Optional[str] = None,
    fan_out: bool = True,
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
    if fan_out and org_id:
        # Telegram / webhook copies go through the durable outbox. Best effort:
        # the in-app notification above is already saved either way.
        try:
            from app.services.alert_channels import enqueue_alerts

            if await enqueue_alerts(db, org_id=org_id, user_id=user_id, notification_id=notif.id,
                                    title=title, message=message, link=link):
                await db.commit()
        except Exception:
            import logging

            await db.rollback()
            logging.getLogger(__name__).exception("alert fan-out failed for notification %s", notif.id)
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
