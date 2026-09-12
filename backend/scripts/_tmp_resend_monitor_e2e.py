"""Prove a monitor alert goes through Resend, then read last_event.

Recipient defaults to delivered@resend.dev so this can run without a verified
domain. That address is Resend's official delivery sink: retrieve then shows
last_event=delivered. Set RESEND_TEST_TO to a real inbox if the account is
allowed to send there (usually only the Resend-account email until a domain
is verified).
"""
import os, sys, asyncio, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from app.core.config import settings
from app.db.session import async_session_maker
from app.models.user import User
from app.services.email_service import email_enabled, retrieve_email
from app.services.creative_fingerprint import CreativeSignature, DiffResult
from app.services import monitor_service

TO = os.getenv("RESEND_TEST_TO", "delivered@resend.dev")


async def wait_for_event(email_id: str, tries: int = 15) -> dict:
    last = {}
    for i in range(tries):
        last = await retrieve_email(email_id) or {}
        event = last.get("last_event")
        print(f"  retrieve #{i+1}: last_event={event!r}")
        if event in ("delivered", "opened", "clicked", "bounced", "complained"):
            return last
        await asyncio.sleep(2)
    return last


async def main():
    print("email_enabled:", email_enabled())
    print("RESEND_FROM set:", bool(settings.RESEND_FROM))
    if not email_enabled():
        print("BLOCKED: RESEND_API_KEY and RESEND_FROM are not both set.")
        sys.exit(2)

    mid = None
    original_email = None
    try:
        async with async_session_maker() as db:
            user = (await db.execute(select(User).where(User.role == "admin").limit(1))).scalar_one()
            from app.services.billing_service import get_or_create_default_org
            org = await get_or_create_default_org(db, user)
            original_email = user.email
            user.email = TO
            await db.commit()
            created = await monitor_service.create_monitor(
                db,
                user=user,
                org_id=org.id,
                name="Resend delivery probe",
                query=f"resend-probe-{int(time.time())}",
                cadence="daily",
                notify_in_app=True,
                notify_email=True,
            )
            mid = created["id"]
            print("monitor", mid, "to", TO)

        result = DiffResult(
            new=[
                CreativeSignature(
                    identity="probe",
                    content="probe",
                    anchor="headline",
                    headline="New competitor ad (Resend probe)",
                    body="This is a delivery proof, not a real scrape.",
                    cta="View",
                    platform="meta",
                    landing_domain="example.com",
                )
            ],
            changed=[],
            killed=[],
            pending_misses=[],
            recovered=[],
            unchanged=0,
        )
        send = await monitor_service._fan_out(mid, "probe-run", result)
        print("fan_out accepted:", bool(send), "id:", getattr(send, "email_id", None), "error:", getattr(send, "error", None))
        if not send or not send.email_id:
            sys.exit(1)

        retrieved = await wait_for_event(send.email_id)
        last_event = retrieved.get("last_event")
        print("subject:", retrieved.get("subject"))
        print("from:", retrieved.get("from"))
        print("to:", retrieved.get("to"))
        print("last_event:", last_event)
        if last_event != "delivered":
            print("FAIL: Resend did not report delivered")
            sys.exit(1)
        print("PASS: Resend last_event=delivered")
    finally:
        if mid and original_email is not None:
            await _cleanup(mid, original_email)


async def _cleanup(monitor_id: str, original_email: str):
    async with async_session_maker() as db:
        for table in ("monitor_events", "monitor_creatives", "monitor_runs"):
            await db.execute(text(f"DELETE FROM {table} WHERE monitor_id = :i"), {"i": monitor_id})
        await db.execute(text("DELETE FROM monitors WHERE id = :i"), {"i": monitor_id})
        user = (await db.execute(select(User).where(User.role == "admin").limit(1))).scalar_one()
        user.email = original_email
        await db.commit()


asyncio.run(main())
