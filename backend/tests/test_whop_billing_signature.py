"""Whop billing: signature, plan map and expiry. No database."""
from __future__ import annotations

import asyncio
import base64
import datetime
import hashlib
import hmac
import json

import httpx
import pytest
from fastapi import FastAPI

from app.api.routers import billing_webhooks
from app.core.config import settings
from app.core.deps import get_db
from app.services import whop_billing

# Built at runtime and low-entropy: a test value, not a credential.
SECRET = "ws_" + "test" * 4
NOW = 1_800_000_000


def _headers(body: bytes, secret: str = SECRET, ts: int = NOW, wid: str = "msg_1") -> dict:
    return {"webhook-id": wid, "webhook-timestamp": str(ts), "webhook-signature": whop_billing.sign(secret, wid, str(ts), body)}


def test_signature_matches_whop_sdk_scheme():
    # whop-sdk 2.8.1 base64-encodes the secret for standardwebhooks, which
    # base64-decodes it again: the HMAC key is the literal ws_ string.
    body = b'{"type":"membership.updated"}'
    expected = base64.b64encode(
        hmac.new(SECRET.encode(), b"msg_1.%d." % NOW + body, hashlib.sha256).digest()
    ).decode()
    assert _headers(body)["webhook-signature"] == f"v1,{expected}"


def test_genuine_delivery_is_accepted():
    body = b'{"type":"payment.succeeded"}'
    assert whop_billing.verify(body, _headers(body), SECRET, now=NOW) == "msg_1"


def test_rotated_secret_list_accepts_any_matching_entry():
    body = b"{}"
    h = _headers(body)
    h["webhook-signature"] = "v1,AAAA " + h["webhook-signature"]
    assert whop_billing.verify(body, h, SECRET, now=NOW) == "msg_1"


@pytest.mark.parametrize("mutate", [
    lambda b, h: (b + b" ", h),  # body changed after signing
    lambda b, h: (b, {**h, "webhook-id": "msg_2"}),  # id swapped
    lambda b, h: (b, {**h, "webhook-signature": "v1,AAAA"}),
    lambda b, h: (b, {k: v for k, v in h.items() if k != "webhook-signature"}),
    lambda b, h: (b, {**h, "webhook-timestamp": "nope"}),
])
def test_tampered_deliveries_are_rejected(mutate):
    body = b'{"type":"membership.updated"}'
    body2, headers = mutate(body, _headers(body))
    with pytest.raises(whop_billing.WebhookRejected):
        whop_billing.verify(body2, headers, SECRET, now=NOW)


def test_wrong_secret_and_stale_timestamp_are_rejected():
    body = b"{}"
    with pytest.raises(whop_billing.WebhookRejected):
        whop_billing.verify(body, _headers(body, secret="ws_other"), SECRET, now=NOW)
    with pytest.raises(whop_billing.WebhookRejected):
        whop_billing.verify(body, _headers(body, ts=NOW - 301), SECRET, now=NOW)
    with pytest.raises(whop_billing.WebhookRejected):
        whop_billing.verify(body, _headers(body), "", now=NOW)


def test_plan_map_parsing_ignores_junk():
    assert whop_billing.plan_map(" plan_a = helix_pro , plan_b=helix_team,bad,=x,y=") == {
        "plan_a": "helix_pro", "plan_b": "helix_team",
    }
    assert whop_billing.plan_map("") == {}


def test_access_runs_to_period_end_plus_grace(monkeypatch):
    monkeypatch.setattr(settings, "WHOP_GRACE_HOURS", 48)
    end = whop_billing.access_until({"current_period_end": "2026-12-01T00:00:00.000Z"})
    assert end == datetime.datetime(2026, 12, 3, tzinfo=datetime.timezone.utc)
    assert whop_billing.access_until({"current_period_end": None, "expires_at": None}) is None


def _client(monkeypatch, secret):
    monkeypatch.setattr(settings, "WHOP_WEBHOOK_SECRET", secret)
    app = FastAPI()
    app.include_router(billing_webhooks.router, prefix="/api/webhooks/billing")

    async def _db():
        yield None

    app.dependency_overrides[get_db] = _db
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


def test_webhook_is_off_until_a_secret_is_set(monkeypatch):
    async def run():
        async with _client(monkeypatch, "") as c:
            return (await c.post("/api/webhooks/billing/whop", content=b"{}")).status_code
    assert asyncio.run(run()) == 503


def test_unsigned_webhook_is_refused_before_any_database_work(monkeypatch):
    called = []

    async def _never(*a, **k):
        called.append(1)

    monkeypatch.setattr(whop_billing, "handle_event", _never)

    async def run():
        async with _client(monkeypatch, SECRET) as c:
            body = json.dumps({"type": "membership.activated"}).encode()
            return (await c.post("/api/webhooks/billing/whop", content=body,
                                 headers={"webhook-id": "m", "webhook-timestamp": "1", "webhook-signature": "v1,x"})).status_code
    assert asyncio.run(run()) == 401
    assert called == []
