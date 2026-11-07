"""W8: monitors roll up into one digest per owner per day; email only when asked and configured."""
from __future__ import annotations

import datetime
import uuid
from collections import Counter

import pytest
from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.monitor import Monitor, MonitorEvent, MonitorRun
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.user import User
from app.services import monitor_digest_service as digest
from app.services.email_service import SendResult


def test_summary_counts_only_what_happened():
    assert digest.summarize(Counter({"new_ad": 2, "killed_ad": 1})) == "2 new, 1 stopped"
    assert digest.summarize(Counter()) == ""


def test_email_escapes_monitor_text():
    html = digest.render_email([("<b>x</b>", 'q"<', "1 new")], "https://app/monitors")
    assert "<b>x</b>" not in html and "&lt;b&gt;x&lt;/b&gt;" in html


@pytest.mark.asyncio
async def test_digest_is_sent_once_per_window_and_emails_only_on_opt_in(monkeypatch):
    sent = []

    async def fake_send(**kwargs):
        sent.append(kwargs)
        return SendResult(True, email_id="e1")
    monkeypatch.setattr(digest, "email_enabled", lambda: True)
    monkeypatch.setattr(digest, "send_email", fake_send)

    suffix = uuid.uuid4().hex[:8]
    now = datetime.datetime.now(datetime.timezone.utc)
    async with async_session_maker() as db:
        user = User(id=f"u_{suffix}", email=f"w8-digest-{suffix}@example.com", password_hash="x", role="member")
        db.add(user)
        await db.flush()
        org = Organization(id=f"o_{suffix}", name="Digest", owner_id=user.id, plan="pro")
        db.add(org)
        await db.flush()
        quiet = Monitor(id=f"m1_{suffix}", org_id=org.id, user_id=user.id, name="Quiet", query="q1", notify_email=False)
        loud = Monitor(id=f"m2_{suffix}", org_id=org.id, user_id=user.id, name="Acme", query="acme.com", notify_email=False)
        db.add_all([quiet, loud])
        await db.flush()
        run = MonitorRun(id=f"r_{suffix}", monitor_id=loud.id, status="succeeded")
        db.add(run)
        await db.flush()
        for i, kind in enumerate(("new_ad", "new_ad", "killed_ad")):
            db.add(MonitorEvent(monitor_id=loud.id, run_id=run.id, type=kind, identity_hash=f"h{i}_{suffix}"))
        await db.commit()

    first = await digest.maybe_send_digest(org.id, user.id, now=now)
    assert first == {"monitors": 1, "summary": "2 new, 1 stopped", "emailed": False}  # nobody asked for email
    assert sent == []
    assert await digest.maybe_send_digest(org.id, user.id, now=now + datetime.timedelta(hours=1)) is None

    async with async_session_maker() as db:
        notes = (await db.execute(select(Notification).where(
            Notification.user_id == user.id, Notification.type == digest.DIGEST_TYPE
        ))).scalars().all()
        assert len(notes) == 1 and "Acme" in notes[0].message and "Quiet" not in notes[0].message
        loud_row = await db.get(Monitor, loud.id)
        loud_row.notify_email = True
        db.add(MonitorEvent(monitor_id=loud.id, run_id=run.id, type="copy_changed", identity_hash=f"h9_{suffix}"))
        await db.commit()

    later = await digest.maybe_send_digest(org.id, user.id, now=now + datetime.timedelta(hours=25))
    assert later is not None and later["emailed"] is True
    assert len(sent) == 1 and sent[0]["to"] == user.email and "copy changed" in sent[0]["subject"]
