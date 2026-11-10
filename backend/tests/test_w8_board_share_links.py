"""W8: guest board links are signed, read-only, revocable, expiring and workspace-bound."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import update

from app.db.session import async_session_maker
from app.main import app
from app.models.board_share_link import BoardShareLink
from app.models.creative import Creative
from app.models.creative_score import CreativeScore
from app.models.organization import Organization
from app.models.saved_creative import SavedCreative
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.services import board_share_service as svc

FUTURE = datetime.now(timezone.utc) + timedelta(days=7)


def test_token_round_trip_and_every_tampering_fails():
    token = svc.sign_token("link-1", "org-1", FUTURE)
    claims = svc.verify_token(token)
    assert claims == {"link_id": "link-1", "org_id": "org-1", "exp": int(FUTURE.timestamp())}

    payload, mac = token.split(".")
    other_payload = svc.sign_token("link-1", "org-2", FUTURE).split(".")[0]
    assert svc.verify_token(f"{other_payload}.{mac}") is None  # swapped workspace
    assert svc.verify_token(f"{payload}.{mac[:-2]}xx") is None  # bad signature
    assert svc.verify_token(payload) is None
    assert svc.verify_token("a.b.c") is None
    assert svc.verify_token("x" * 600 + ".y") is None
    assert svc.verify_token(token, now=FUTURE + timedelta(seconds=1)) is None  # expired


def test_link_key_is_separate_from_the_session_secret(monkeypatch):
    token = svc.sign_token("l", "o", FUTURE)
    monkeypatch.setattr(svc.settings, "SECRET_KEY", "a-different-secret-key-for-this-test-only")
    assert svc.verify_token(token) is None


class NoDB:
    async def scalar(self, *_):
        raise AssertionError("query ran")

    async def execute(self, *_):
        raise AssertionError("query ran")


@pytest.mark.asyncio
async def test_forged_or_expired_tokens_never_reach_the_database():
    for token in ("", "garbage", svc.sign_token("l", "o", FUTURE)[:-3] + "abc",
                  svc.sign_token("l", "o", datetime.now(timezone.utc) - timedelta(seconds=5))):
        with pytest.raises(HTTPException) as error:
            await svc.read_guest_board(NoDB(), token)
        assert error.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("collection, days", [("", 7), ("Hooks", 0), ("Hooks", 90), ("Hooks", 365)])
async def test_invalid_create_requests_are_rejected_before_any_query(collection, days):
    with pytest.raises(HTTPException) as error:
        await svc.create_link(NoDB(), object(), collection, days)
    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_guest_link_shows_one_board_only_and_closes_on_revoke_and_expiry():
    suffix = uuid.uuid4().hex[:8]
    async with async_session_maker() as db:
        owner = User(id=f"u_{suffix}", email=f"w8-share-{suffix}@example.com", password_hash="x", role="member")
        other = User(id=f"v_{suffix}", email=f"w8-share-other-{suffix}@example.com", password_hash="x", role="member")
        db.add_all([owner, other])
        await db.flush()
        org = Organization(id=f"o_{suffix}", name="Share", owner_id=owner.id, plan="pro")
        org_b = Organization(id=f"p_{suffix}", name="Other", owner_id=other.id, plan="pro")
        db.add_all([org, org_b])
        await db.flush()
        job = ScrapeJob(id=f"j_{suffix}", org_id=org.id, query="share", status="succeeded")
        db.add(job)
        await db.flush()
        for key, board in (("a", "Hooks"), ("b", "Hooks"), ("c", "Private")):
            cid = f"c_{suffix}_{key}"
            db.add(Creative(id=cid, job_id=job.id, brand_id="brand", brand_name="Brand", platform="meta",
                            format="image", headline=f"headline {key}", days_active=None if key == "b" else 45,
                            impressions_est=9000, data_source="ad_library_scrape"))
            db.add(CreativeScore(creative_id=cid, composite=7.5))
            await db.flush()
            db.add(SavedCreative(user_id=owner.id, org_id=org.id, creative_id=cid, collection_name=board))
        await db.commit()

        assert await svc.list_boards(db, owner) == [{"name": "Hooks", "count": 2}, {"name": "Private", "count": 1}]
        assert await svc.list_boards(db, other) == []

        link = await svc.create_link(db, owner, "Hooks", 7)
        assert link["state"] == "active" and link["url"].startswith("/b/")
        token = link["url"][len("/b/"):]

        with pytest.raises(HTTPException) as missing:
            await svc.create_link(db, owner, "Does not exist", 7)
        assert missing.value.status_code == 404

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8000") as client:
            response = await client.get(f"/api/public/boards/{token}")  # no Authorization header
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            assert "noindex" in response.headers["x-robots-tag"]
            body = response.json()
            assert body["read_only"] is True and body["board"] == "Hooks"
            assert sorted(i["headline"] for i in body["items"]) == ["headline a", "headline b"]
            unknown = next(i for i in body["items"] if i["headline"] == "headline b")
            assert unknown["days_active"] is None  # unknown run length stays unknown
            assert all(i["impressions_est"] is None for i in body["items"])  # not Meta-official
            assert "user_id" not in str(body) and owner.email not in str(body)

            # A validly signed token naming another workspace finds nothing.
            forged = svc.sign_token(link["id"], org_b.id, datetime.fromisoformat(link["expires_at"]))
            assert (await client.get(f"/api/public/boards/{forged}")).status_code == 404

            # Expiry in the row closes the link even though the token's own expiry is later.
            await db.execute(update(BoardShareLink).where(BoardShareLink.id == link["id"])
                             .values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
            await db.commit()
            assert (await client.get(f"/api/public/boards/{token}")).status_code == 404
            await db.execute(update(BoardShareLink).where(BoardShareLink.id == link["id"])
                             .values(expires_at=datetime.fromisoformat(link["expires_at"])))
            await db.commit()
            assert (await client.get(f"/api/public/boards/{token}")).status_code == 200

            # Only the creator can revoke; a revoked link is gone for guests.
            with pytest.raises(HTTPException) as not_theirs:
                await svc.revoke_link(db, other, link["id"])
            assert not_theirs.value.status_code == 404
            revoked = await svc.revoke_link(db, owner, link["id"])
            assert revoked["state"] == "revoked" and revoked["url"] is None
            assert (await client.get(f"/api/public/boards/{token}")).status_code == 404

        listed = await svc.list_links(db, owner, "Hooks")
        assert [item["state"] for item in listed] == ["revoked"]
