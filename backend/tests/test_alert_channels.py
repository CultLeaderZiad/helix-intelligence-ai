"""3.1 Alerts: Telegram and signed webhooks, on a real database."""
import hashlib
import hmac
import json
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text

from app.core.config import settings
from app.core.tenancy import apply_tenant_context, tenant_scope
from app.db.session import async_session_maker
from app.models.notification import Notification
from app.models.notification_channel import NotificationChannel
from app.models.organization import Organization
from app.models.user import User
from app.services import alert_channels, notification_service, safe_fetch


async def _org(suffix):
    async with async_session_maker() as db:
        user = User(id=f"u_al_{suffix}", email=f"al-{suffix}@example.com", password_hash="x", role="member")
        db.add(user)
        await db.flush()
        db.add(Organization(id=f"o_al_{suffix}", name="AL", owner_id=user.id, plan="pro"))
        await db.commit()
    return f"o_al_{suffix}", f"u_al_{suffix}"


@pytest.fixture
def public_dns(monkeypatch):
    monkeypatch.setattr(safe_fetch, "_public_ip", lambda host, port, resolve=None: "93.184.216.34")


async def _in_scope(org_id, fn):
    with tenant_scope([org_id], "", platform_admin=False, enforce=True):
        async with async_session_maker() as db:
            await apply_tenant_context(db)
            return await fn(db)


@pytest.mark.asyncio
async def test_webhook_needs_https_and_a_public_host(public_dns, monkeypatch):
    org, user = await _org(uuid.uuid4().hex[:8])
    for bad in ("http://hooks.example.com/x", "https://localhost/x"):
        with pytest.raises(HTTPException) as exc:
            await _in_scope(org, lambda db: alert_channels.create_webhook(db, org, user, bad))
        assert exc.value.status_code == 422
    out = await _in_scope(org, lambda db: alert_channels.create_webhook(db, org, user, "https://hooks.example.com/helix"))
    assert out["signing_secret"].startswith("whsec_")
    assert "hooks.example.com" in out["channel"]["label"] and "/helix" not in out["channel"]["label"]
    # Plan default: one webhook.
    with pytest.raises(HTTPException) as exc:
        await _in_scope(org, lambda db: alert_channels.create_webhook(db, org, user, "https://other.example.com/x"))
    assert exc.value.detail["code"] == "alert_channel_limit"


@pytest.mark.asyncio
async def test_webhook_to_a_private_address_is_refused():
    org, user = await _org(uuid.uuid4().hex[:8])
    for bad in ("https://10.0.0.5/x", "https://127.0.0.1/x", "https://169.254.169.254/latest"):
        with pytest.raises(HTTPException) as exc:
            await _in_scope(org, lambda db: alert_channels.create_webhook(db, org, user, bad))
        assert exc.value.detail["code"] == "webhook_url_blocked"


@pytest.mark.asyncio
async def test_notifications_fan_out_to_the_outbox_up_to_the_daily_cap(public_dns, monkeypatch):
    monkeypatch.setattr(settings, "ALERT_DEFAULT_PER_DAY", 2)
    org, user = await _org(uuid.uuid4().hex[:8])
    await _in_scope(org, lambda db: alert_channels.create_webhook(db, org, user, "https://hooks.example.com/h"))
    for i in range(3):
        await _in_scope(org, lambda db: notification_service.create_notification(
            db, user_id=user, org_id=org, title=f"New ads {i}", message="2 new ads", link="/monitors"))

    async def count(db):
        return await db.scalar(text("SELECT count(*) FROM work_items WHERE org_id = :o AND kind = 'alert'"), {"o": org})
    assert await _in_scope(org, count) == 2  # the third stays in-app only


@pytest.mark.asyncio
async def test_webhook_delivery_is_signed_and_failures_disable_the_channel(public_dns, monkeypatch):
    monkeypatch.setattr(settings, "ALERT_MAX_CONSECUTIVE_FAILURES", 2)
    org, user = await _org(uuid.uuid4().hex[:8])
    created = await _in_scope(org, lambda db: alert_channels.create_webhook(db, org, user, "https://hooks.example.com/h"))
    secret, channel_id = created["signing_secret"], created["channel"]["id"]
    sent = []

    class Res:
        def __init__(self, code):
            self.status_code = code

    status = {"code": 200}

    async def fake_post(url, content, headers=None, timeout=10.0):
        sent.append((url, content, headers))
        return Res(status["code"])

    monkeypatch.setattr(safe_fetch, "safe_http_post_async", fake_post)
    payload = {"channel_id": channel_id, "notification_id": "n1", "title": "T", "message": "M", "link": "/monitors"}

    assert await alert_channels.deliver(org, payload) == "sent"
    url, body, headers = sent[0]
    assert url == "https://hooks.example.com/h"
    expected = "v1=" + hmac.new(secret.encode(), headers["X-Helix-Timestamp"].encode() + b"." + body, hashlib.sha256).hexdigest()
    assert headers["X-Helix-Signature"] == expected
    doc = json.loads(body)
    assert doc["type"] == "helix.alert" and doc["link"].endswith("/monitors")

    status["code"] = 500
    with pytest.raises(RuntimeError):
        await alert_channels.deliver(org, payload)  # raises so the outbox retries
    assert await alert_channels.deliver(org, payload) == "disabled"

    async def state(db):
        ch = (await db.execute(select(NotificationChannel).where(NotificationChannel.id == channel_id))).scalar_one()
        notes = (await db.execute(select(Notification).where(Notification.org_id == org))).scalars().all()
        return ch, notes
    ch, notes = await _in_scope(org, state)
    assert ch.status == "disabled" and ch.consecutive_failures == 2
    assert any("turned off" in n.title.lower() for n in notes)
    assert await alert_channels.deliver(org, payload) == "skipped"


@pytest.mark.asyncio
async def test_telegram_link_flow(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "helix_test_bot")
    org, user = await _org(uuid.uuid4().hex[:8])
    out = await _in_scope(org, lambda db: alert_channels.start_telegram_link(db, org, user))
    assert out["channel"]["status"] == "pending"
    code = out["link"].split("start=")[1]
    assert out["link"].startswith("https://t.me/helix_test_bot?start=")

    async with async_session_maker() as db:
        assert await alert_channels.complete_telegram_link(db, "wrong-code", 42, "x") is False
    async with async_session_maker() as db:
        assert await alert_channels.complete_telegram_link(db, code, 4242, "Growth team") is True
    async with async_session_maker() as db:
        assert await alert_channels.complete_telegram_link(db, code, 4242, "again") is False  # single use

    async def view(db):
        return [alert_channels.public_view(c) for c in await alert_channels.list_channels(db, org)]
    (ch,) = await _in_scope(org, view)
    assert ch["status"] == "active" and ch["label"] == "Telegram: Growth team"
    assert "4242" not in json.dumps(ch)


@pytest.mark.asyncio
async def test_telegram_disabled_without_bot(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "")
    org, user = await _org(uuid.uuid4().hex[:8])
    with pytest.raises(HTTPException) as exc:
        await _in_scope(org, lambda db: alert_channels.start_telegram_link(db, org, user))
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_channels_are_invisible_to_another_workspace(public_dns):
    """Checked as helix_app so RLS applies."""
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.db.session import worker_engine

    org, user = await _org(uuid.uuid4().hex[:8])
    other, _ = await _org(uuid.uuid4().hex[:8])
    await _in_scope(org, lambda db: alert_channels.create_webhook(db, org, user, "https://hooks.example.com/h"))
    engine = create_async_engine(worker_engine.url, connect_args={"statement_cache_size": 0})
    seen = {}
    try:
        async with engine.connect() as conn:
            for scope in (org, other):
                await conn.execute(text("BEGIN"))
                await conn.execute(text("SET LOCAL ROLE helix_app"))
                await conn.execute(text("SELECT set_config('helix.enforce', '1', true)"))
                await conn.execute(text("SELECT set_config('helix.platform_admin', '0', true)"))
                await conn.execute(text("SELECT set_config('helix.org_ids', :ids, true)"), {"ids": scope})
                seen[scope] = (await conn.execute(
                    text("SELECT count(*) FROM notification_channels WHERE org_id = :o"), {"o": org})).scalar_one()
                await conn.execute(text("COMMIT"))
    finally:
        await engine.dispose()
    assert seen == {org: 1, other: 0}


def test_telegram_webhook_refuses_a_wrong_secret(monkeypatch):
    import asyncio

    import httpx
    from fastapi import FastAPI

    from app.api.routers import alerts
    from app.core.deps import get_db

    app = FastAPI()
    app.include_router(alerts.telegram_router, prefix="/api/telegram")

    async def _db():
        yield None

    app.dependency_overrides[get_db] = _db

    async def post(headers):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            return (await c.post("/api/telegram/webhook", json={"message": {"text": "/start x", "chat": {"id": 1}}},
                                 headers=headers)).status_code

    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    assert asyncio.run(post({})) == 503
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "s3cret")
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "b")
    assert asyncio.run(post({"X-Telegram-Bot-Api-Secret-Token": "nope"})) == 401
