"""Prove a failed monitor run notifies and does not refund."""
import os, sys, time, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from app.db.session import async_session_maker
from app.models.user import User
from app.models.notification import Notification
from app.models.monitor import Monitor
from app.services import monitor_service


async def main():
    async with async_session_maker() as db:
        user = (await db.execute(select(User).where(User.role == "admin").limit(1))).scalar_one()
        from app.services.billing_service import get_or_create_default_org
        org = await get_or_create_default_org(db, user)
        created = await monitor_service.create_monitor(
            db,
            user=user,
            org_id=org.id,
            name="Failure notify probe",
            query=f"fail-notify-probe-{int(time.time())}",
            cadence="daily",
            notify_in_app=True,
            notify_email=True,
        )
        mid = created["id"]
        uid = user.id

    await monitor_service._notify_run_failed(mid, "Provider returned HTTP 500 (probe).")

    async with async_session_maker() as db:
        notif = (
            await db.execute(
                select(Notification)
                .where(
                    Notification.user_id == uid,
                    Notification.title == "Monitor run failed",
                    Notification.link == f"/monitors?id={mid}",
                )
                .order_by(Notification.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        refunds = (
            await db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM usage_logs
                    WHERE operation LIKE 'refund%'
                      AND metadata_json::text LIKE :needle
                    """
                ),
                {"needle": f"%{mid}%"},
            )
        ).scalar()
        import_has_refund = "refund" in open(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "services", "monitor_service.py"),
            encoding="utf-8",
        ).read().split("from app.services.billing_service")[1].split(")", 1)[0]

        print("notification_created:", bool(notif))
        print("notification_type:", getattr(notif, "type", None))
        print("mentions_charge:", "charged" in ((notif.message if notif else "") or "").lower())
        print("refund_rows_for_monitor:", int(refunds or 0))
        print("monitor_service_imports_refund:", import_has_refund)

        await db.execute(text("DELETE FROM notifications WHERE id = :i"), {"i": notif.id} if notif else {"i": ""})
        for table in ("monitor_events", "monitor_creatives", "monitor_runs"):
            await db.execute(text(f"DELETE FROM {table} WHERE monitor_id = :i"), {"i": mid})
        await db.execute(text("DELETE FROM monitors WHERE id = :i"), {"i": mid})
        await db.commit()

    if not notif or int(refunds or 0) != 0 or import_has_refund:
        sys.exit(1)
    print("PASS: failure notifies in-app, no refund")


asyncio.run(main())
