"""W8 pricing: full admins edit each plan's public card; /api/public/pricing shows listed plans only."""
from __future__ import annotations

import uuid

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import async_session_maker
from app.main import app
from app.models.user import User
from app.schemas.pricing import PlanPricing


@pytest.fixture(autouse=True)
def _no_rate_limit(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8000")


def test_pricing_card_is_trimmed_and_bounded():
    card = PlanPricing(features={"en": ["  Discover  search ", "", *[f"f{i}" for i in range(20)]], "ar": []})
    assert card.features.en[0] == "Discover search"
    assert len(card.features.en) == 12
    assert card.listed is False and card.cta == "trial"
    with pytest.raises(ValidationError):
        PlanPricing(cta="checkout")
    with pytest.raises(ValidationError):
        PlanPricing(order=500)


async def _user(role: str) -> tuple[str, str]:
    sfx = uuid.uuid4().hex[:10]
    password = f"Pw-{sfx}-Aa1!"
    async with async_session_maker() as db:
        user = User(
            id=f"pr_{sfx}", email=f"w8-pricing-{role}-{sfx}@example.com",
            password_hash=get_password_hash(password), role=role, is_platform_admin=role == "admin",
        )
        db.add(user)
        await db.commit()
    return user.email, password


async def _token(client, email, password) -> dict:
    r = await client.post("/api/auth/sign-in", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_admin_edits_pricing_and_only_listed_plans_are_public():
    async with _client() as client:
        admin = await _token(client, *await _user("admin"))
        name = f"Pro {uuid.uuid4().hex[:6]}"
        card = {
            "listed": False, "order": 1, "highlight": True, "cta": "contact",
            "tagline": {"en": "For growing teams", "ar": "للفرق النامية"},
            "features": {"en": ["5 monitors", "Unlimited boards"], "ar": ["5 مراقبات", "لوحات بلا حدود"]},
        }
        created = await client.post("/api/admin/plans", headers=admin, json={"name": name, "price_monthly": 29, "pricing": card})
        assert created.status_code == 200, created.text
        plan_id = created.json()["id"]
        assert created.json()["pricing"]["features"]["en"] == ["5 monitors", "Unlimited boards"]

        public = (await client.get("/api/public/pricing")).json()
        assert public["trial_days"] == settings.SIGNUP_TRIAL_DAYS
        assert plan_id not in [p["id"] for p in public["plans"]]

        card["listed"] = True
        updated = await client.put(f"/api/admin/plans/{plan_id}", headers=admin, json={"pricing": card})
        assert updated.status_code == 200, updated.text
        listed = [p for p in (await client.get("/api/public/pricing")).json()["plans"] if p["id"] == plan_id]
        assert listed and listed[0]["price_monthly"] == 29
        assert listed[0]["pricing"]["tagline"]["ar"] == "للفرق النامية"
        assert "feature_flags" not in listed[0]  # internal plan config stays private

        await client.delete(f"/api/admin/plans/{plan_id}", headers=admin)


@pytest.mark.asyncio
async def test_only_full_admins_can_edit_pricing():
    async with _client() as client:
        customer = await _token(client, *await _user("customer"))
        r = await client.post("/api/admin/plans", headers=customer, json={"name": "Nope", "pricing": {"listed": True}})
        assert r.status_code == 403
        assert (await client.get("/api/public/pricing")).status_code == 200  # public read needs no sign-in
