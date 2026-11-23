"""Whop checkout links: off until configured, workspace id set by the server. No database."""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services import whop_billing


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(settings, "WHOP_API_KEY", "apik_test")
    monkeypatch.setattr(settings, "WHOP_COMPANY_ID", "biz_test")
    monkeypatch.setattr(settings, "WHOP_PLAN_MAP", "plan_whop_pro=helix_pro")
    monkeypatch.setattr(settings, "WHOP_API_BASE", "https://whop.test/api/v1")


def _status(coro):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(coro)
    return exc.value.status_code


def test_checkout_is_off_without_key_or_plan_map(monkeypatch):
    monkeypatch.setattr(settings, "WHOP_API_KEY", "")
    monkeypatch.setattr(settings, "WHOP_PLAN_MAP", "plan_whop_pro=helix_pro")
    assert _status(whop_billing.create_checkout("o1", "helix_pro", "https://app/x")) == 503
    monkeypatch.setattr(settings, "WHOP_API_KEY", "k")
    monkeypatch.setattr(settings, "WHOP_PLAN_MAP", "")
    assert _status(whop_billing.create_checkout("o1", "helix_pro", "https://app/x")) == 503


def test_unmapped_plan_cannot_be_bought(configured):
    assert _status(whop_billing.create_checkout("o1", "helix_other", "https://app/x")) == 404


def test_checkout_carries_the_workspace_in_metadata(configured, monkeypatch):
    sent = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent["url"] = str(request.url)
        sent["auth"] = request.headers.get("authorization")
        sent["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "ch_1", "purchase_url": "https://whop.com/checkout/ch_1/"})

    real = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    url = asyncio.run(whop_billing.create_checkout("o_owner", "helix_pro", "https://app/settings?billing=returned"))
    assert url == "https://whop.com/checkout/ch_1/"
    assert sent["url"] == "https://whop.test/api/v1/checkout_configurations"
    assert sent["auth"] == "Bearer apik_test"
    assert sent["body"] == {
        "variant_id": "plan_whop_pro",
        "redirect_url": "https://app/settings?billing=returned",
        "metadata": {"helix_org_id": "o_owner"},
        "account_id": "biz_test",
    }


def test_provider_errors_become_a_502_without_leaking_details(configured, monkeypatch):
    real = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real(
        transport=httpx.MockTransport(lambda r: httpx.Response(401, json={"error": "bad key apik_test"})), **kw))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(whop_billing.create_checkout("o1", "helix_pro", "https://app/x"))
    assert exc.value.status_code == 502
    assert "apik_test" not in json.dumps(exc.value.detail)
