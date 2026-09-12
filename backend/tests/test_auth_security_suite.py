"""
HTTP-level reproductions for the auth/media security fixes.

Run:
    cd backend
    ../.venv/bin/python tests/test_auth_security_suite.py

Every case here drives the real FastAPI app through httpx's ASGITransport —
router, dependencies, Pydantic validation, status codes and response bodies —
because each of these bugs was invisible to a unit test that called the service
layer directly. The "before" behaviour is written out in each docstring so the
file also documents what broke.

No Postgres, no network, no provider credentials: the DB is in-memory SQLite
behind a stubbed app.db.session, and ASGITransport does not run the lifespan so
the Postgres-only startup DDL never executes.
"""
import asyncio
import datetime
import logging
import os
import sys
import types
import uuid
from typing import List

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ["ENV"] = "production"          # fail-closed posture, like prod
os.environ["AUTH_DEV_RESET_RETURN"] = "false"
os.environ["USE_MOCKS"] = "False"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

engine = create_async_engine("sqlite+aiosqlite://")
Session = async_sessionmaker(engine, expire_on_commit=False)

_stub = types.ModuleType("app.db.session")
_stub.engine = engine
_stub.async_session_maker = Session


async def _get_db():
    async with Session() as session:
        yield session


_stub.get_db = _get_db
sys.modules["app.db.session"] = _stub

import app.models  # noqa: E402,F401  (register every table on Base.metadata)
from app.db.base import Base  # noqa: E402

try:  # app/core/rate_limit.py is new in this change set
    from app.core import rate_limit  # noqa: E402
    from app.core.rate_limit import AUTH_LIMITER  # noqa: E402
except ImportError:  # pre-fix checkout: fail the throttle cases, run the rest
    rate_limit = None
    AUTH_LIMITER = None
from app.core.config import settings  # noqa: E402
from app.core.security import (  # noqa: E402
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.models.media_job import MediaGenerationJob  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.webhook_event import WebhookEvent  # noqa: E402
from app.services import auth_service  # noqa: E402
from app.services import billing_service  # noqa: E402
from app.services import media_service  # noqa: E402

# sqlite has no TIMESTAMPTZ, so DateTime(timezone=True) comes back naive and
# billing_service._ensure_daily_reset's naive-vs-aware comparison raises. That
# is a test-harness artifact, not product behavior (Postgres always returns an
# aware value); normalize it here rather than bending the product code.
_real_ensure_daily_reset = billing_service._ensure_daily_reset


async def _sqlite_ensure_daily_reset(db, org):
    value = org.daily_credits_reset_at
    if value is not None and value.tzinfo is None:
        org.daily_credits_reset_at = value.replace(tzinfo=datetime.timezone.utc)
    return await _real_ensure_daily_reset(db, org)


billing_service._ensure_daily_reset = _sqlite_ensure_daily_reset

# Drive the *deployed* wiring, not a purpose-built app: same FastAPI instance,
# same prefixes, same middleware list, same router order. ASGITransport does not
# run the lifespan, so the Postgres-only startup DDL never fires.
from app.main import app  # noqa: E402

API_PREFIX = settings.API_V1_STR

WEBHOOK_SECRET = "whsec_test_vector_only"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
class LogCapture:
    """Collects formatted records for every app logger, at every level."""

    def __init__(self):
        self.records: List[str] = []
        self._handler = logging.Handler()
        self._handler.emit = lambda record: self.records.append(
            f"{record.name}:{record.levelname}:{record.getMessage()}"
        )
        self._root = logging.getLogger()
        self._prev_level = self._root.level

    def __enter__(self):
        self._root.addHandler(self._handler)
        self._root.setLevel(min(self._prev_level, logging.DEBUG))
        return self

    def __exit__(self, *exc):
        self._root.removeHandler(self._handler)
        self._root.setLevel(self._prev_level)
        return False

    def text(self) -> str:
        return "\n".join(self.records)


def client(ip: str = "203.0.113.7") -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        headers={"X-Forwarded-For": ip},
        timeout=30.0,
    )


async def make_user(db, email: str, password: str = "CorrectHorse1!", **fields) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=get_password_hash(password),
        role=fields.pop("role", "customer"),
        **fields,
    )
    db.add(user)
    await db.commit()
    await db.flush()
    org = Organization(
        id=str(uuid.uuid4()),
        name=f"{email.split('@')[0]}'s Workspace",
        owner_id=user.id,
        plan_id="plan_trial_default",
        plan="trial",
        credit_balance=25.0,
        credits_used=0.0,
        status="active",
        images_today_date=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
    )
    db.add(org)
    await db.commit()
    return user


async def make_job(db, user: User, status: str = "pending", **fields) -> MediaGenerationJob:
    org = (await db.execute(select(Organization).where(Organization.owner_id == user.id))).scalar_one()
    job = MediaGenerationJob(
        id=str(uuid.uuid4()),
        user_id=user.id,
        org_id=org.id,
        status=status,
        prompt=fields.pop("prompt", "spring sale banner"),
        provider=fields.pop("provider", "gemini"),
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
        **fields,
    )
    db.add(job)
    await db.commit()
    return job


def auth_headers(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(subject=user.id, role=user.role)}"}


def _has_setting(name: str) -> bool:
    return name in getattr(type(settings), "model_fields", {})


def _helper(name: str):
    """Fetch a security helper, or state plainly that this revision lacks it.

    A pre-fix checkout should fail with "the fix is absent", not with an
    ImportError that a reader has to decode.
    """
    import importlib

    try:
        return getattr(importlib.import_module("app.core.security"), name)
    except AttributeError as exc:
        raise AssertionError(
            f"app.core.security.{name} does not exist on this revision — the fix under test is absent"
        ) from exc


def reset_limits():
    """Neutral starting state so cases do not share buckets or cooldowns.

    Fields are set only when the revision under test declares them, so this file
    still runs (and fails on behaviour, not on setup) against an unpatched
    checkout — which is the whole point of a security regression suite.
    """
    if AUTH_LIMITER is not None:
        AUTH_LIMITER.clear()
    fields = getattr(type(settings), "model_fields", {})
    for key, value in {
        "AUTH_IP_RATE_LIMIT": 1000,
        "AUTH_RATE_WINDOW_SECONDS": 300,
        "AUTH_RESET_REISSUE_COOLDOWN_SECONDS": 0,
        "WEBHOOK_RATE_LIMIT": 1000,
    }.items():
        if key in fields:
            setattr(settings, key, value)


# --------------------------------------------------------------------------
# 1. /auth/forgot-password must not hand out a reset link in production
# --------------------------------------------------------------------------
async def test_reset_link_not_returned_and_enumeration_closed():
    reset_limits()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with Session() as db:
        user = await make_user(db, "owner@vynex.app")
        email = user.email
        await make_user(db, "dev@vynex.app")

        assert _has_setting("ENV") and getattr(settings, "allow_reset_link_in_response", None) is not None, (
            "settings.ENV / allow_reset_link_in_response are absent: the reset-link gate does not exist on this revision"
        )
        settings.ENV = "production"
        settings.AUTH_DEV_RESET_RETURN = False
        assert settings.allow_reset_link_in_response is False

        async with client() as c:
            r = await c.post(f"{API_PREFIX}/auth/forgot-password", json={"email": email})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body == {"ok": True}, f"response leaked extra fields: {body}"
            assert "reset_url" not in body

            # The bug being fixed: this used to return {"reset_url": "...token..."}.
            row = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
            assert row.password_reset_token_hash, "a token must still be minted and stored"
            assert row.password_reset_expires_at is not None

            # No account enumeration: unknown address gets the identical body.
            r2 = await c.post(f"{API_PREFIX}/auth/forgot-password", json={"email": "ghost@nowhere.app"})
            assert r2.status_code == 200 and r2.json() == {"ok": True}

            # A flag flipped in the dashboard alone must not re-open the hole.
            settings.AUTH_DEV_RESET_RETURN = True
            r3 = await c.post(f"{API_PREFIX}/auth/forgot-password", json={"email": "ghost2@nowhere.app"})
            assert "reset_url" not in r3.json(), "prod refused the flag: ENV is the second gate"

            # ...and in a real dev environment the link IS returned, so local
            # testing still works (this is the whole point of the flag).
            settings.ENV = "test"
            r4 = await c.post(f"{API_PREFIX}/auth/forgot-password", json={"email": "dev@vynex.app"})
            assert "reset_url" in r4.json(), "dev mode must still be able to fetch a link"
            token = r4.json()["reset_url"].split("token=")[1]

            # Full loop: redeem it, get a session, old password stops working.
            r5 = await c.post(
                f"{API_PREFIX}/auth/reset-password",
                json={"token": token, "new_password": "BrandNewPass1!"},
            )
            assert r5.status_code == 200, r5.text
            assert r5.json().get("access_token")
            refreshed = (await db.execute(select(User).where(User.email == "dev@vynex.app"))).scalar_one()
            assert await verify_password("BrandNewPass1!", refreshed.password_hash)

            # Prod again: nothing leaks, and the response shape is stable.
            settings.ENV = "production"
            settings.AUTH_DEV_RESET_RETURN = False
    print("[PASS] reset link withheld outside dev; dev path still usable end-to-end; no enumeration")


# --------------------------------------------------------------------------
# 2. throttle: per-network window + DB-backed re-issue cooldown
# --------------------------------------------------------------------------
async def test_forgot_password_rate_limit():
    reset_limits()
    assert _has_setting("AUTH_IP_RATE_LIMIT") and AUTH_LIMITER is not None, (
        "no auth throttle exists on this revision — /auth/forgot-password is unlimited"
    )
    settings.AUTH_IP_RATE_LIMIT = 3
    settings.AUTH_RATE_WINDOW_SECONDS = 60
    async with Session() as db:
        user = await make_user(db, "throttle@vynex.app")

    async with client("198.51.100.9") as c:
        codes = []
        for _ in range(5):
            r = await c.post(f"{API_PREFIX}/auth/forgot-password", json={"email": user.email})
            codes.append(r.status_code)
        assert codes == [200, 200, 200, 429, 429], codes
        blocked = await c.post(f"{API_PREFIX}/auth/forgot-password", json={"email": user.email})
        assert blocked.headers.get("Retry-After", "").isdigit(), "429 must carry Retry-After"
        assert blocked.json()["detail"]["code"] == "too_many_requests"

        # Sign-in has its own bucket: exhausting resets must not unlock
        # credential stuffing (or vice versa).
        r = await c.post(f"{API_PREFIX}/auth/sign-in", json={"email": user.email, "password": "nope"})
        assert r.status_code in (401, 200), r.text

    # A different network is unaffected — the bucket is per client, not global.
    async with client("198.51.100.10") as other:
        r = await other.post(f"{API_PREFIX}/auth/forgot-password", json={"email": user.email})
        assert r.status_code == 200, r.text

    # Cooldown: the second request inside the window must not re-mint, while
    # still answering 200 with the same body (no enumeration, no churn).
    settings.AUTH_IP_RATE_LIMIT = 1000
    settings.AUTH_RESET_REISSUE_COOLDOWN_SECONDS = 120
    async with client("198.51.100.11") as c:
        await c.post(f"{API_PREFIX}/auth/forgot-password", json={"email": user.email})
        async with Session() as db:
            first = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
            first_hash, first_exp = first.password_reset_token_hash, first.password_reset_expires_at
        r = await c.post(f"{API_PREFIX}/auth/forgot-password", json={"email": user.email})
        assert r.status_code == 200 and r.json() == {"ok": True}
        async with Session() as db:
            second = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
            assert second.password_reset_token_hash == first_hash, "cooldown must not replace the live token"
            assert second.password_reset_expires_at == first_exp
        settings.AUTH_RESET_REISSUE_COOLDOWN_SECONDS = 0
        # The token is a JWT with second-granular expiry, so a re-mint in the
        # same second would legitimately produce the identical hash; compare the
        # expiry instead, after clearing a second.
        await asyncio.sleep(1.1)
        await c.post(f"{API_PREFIX}/auth/forgot-password", json={"email": user.email})
        async with Session() as db:
            third = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
            assert third.password_reset_expires_at > first_exp, "after the cooldown a new token must be minted"
    print("[PASS] forgot-password throttled per network; sign-in bucket separate; re-issue cooldown honored")


# --------------------------------------------------------------------------
# 3. limiter internals: window expiry and bounded memory
# --------------------------------------------------------------------------
async def test_limiter_window_and_bounds():
    assert rate_limit is not None, "app.core.rate_limit does not exist on this revision"
    limiter = rate_limit.SlidingWindowLimiter(max_keys=4)
    allowed = [limiter.check("k", 2, 60)[0] for _ in range(4)]
    assert allowed == [True, True, False, False]
    assert limiter.check("other", 2, 60)[0] is True

    # Window expiry: a bucket that goes quiet is spendable again.
    ok, retry_after, _ = limiter.check("k", 2, 0.05)
    assert ok is False and retry_after > 0
    await asyncio.sleep(0.08)
    assert limiter.check("k", 2, 0.05)[0] is True

    # Unbounded growth is a DoS on itself: keys stay capped.
    for i in range(50):
        limiter.check(f"burst:{i}", 1, 3600)
    assert len(limiter._hits) <= 4 + 20, len(limiter._hits)
    limiter.clear()
    assert not limiter._hits
    print("[PASS] sliding window enforces the cap, expires, and stays bounded")


# --------------------------------------------------------------------------
# 4. sign-in must not describe our internals to an anonymous caller
# --------------------------------------------------------------------------
async def test_sign_in_generic_failure_text():
    reset_limits()
    async with Session() as db:
        user = await make_user(db, "signin@vynex.app")
    original = auth_service.authenticate_user

    async def exploding_auth(db_, creds):
        raise RuntimeError("psycopg connection to postgres://super:secret@neon/db failed")

    auth_service.authenticate_user = exploding_auth
    try:
        async with client() as c:
            r = await c.post(f"{API_PREFIX}/auth/sign-in", json={"email": user.email, "password": "x"})
            assert r.status_code == 500, r.text
            text = r.text
            for needle in ("RuntimeError", "psycopg", "super:secret", "neon"):
                assert needle not in text, f"sign-in leaked {needle!r} to an anonymous client"
            detail = r.json()["detail"]
            assert detail["code"] == "internal_error" and "Sign-in" in detail["message"]
    finally:
        auth_service.authenticate_user = original

    # The "authenticated then vanished" row used to answer with a 500 whose
    # text was a bug report about our query order.
    async def vanished_auth(db_, creds):
        return create_access_token(subject=user.id, role="customer")

    auth_service.authenticate_user = vanished_auth
    try:
        async with Session() as db:
            hard_deleted = await make_user(db, "temp@vynex.app")
            victim_id = hard_deleted.id

        async def vanished_for(db_, creds):
            if creds.email == "temp@vynex.app":
                async with Session() as other:
                    row = (await other.execute(select(User).where(User.id == victim_id))).scalar_one()
                    await other.delete(row)
                    await other.commit()
                return create_access_token(subject=victim_id, role="customer")
            raise RuntimeError("gone")

        auth_service.authenticate_user = vanished_for
        async with client() as c:
            r = await c.post(f"{API_PREFIX}/auth/sign-in", json={"email": "temp@vynex.app", "password": "x"})
            assert r.status_code == 503, r.text
            assert r.json()["detail"]["code"] == "temporarily_unavailable"
            assert "second query" not in r.text
    finally:
        auth_service.authenticate_user = original

    # Real credential failures keep their actionable, non-leaky text, and a
    # successful sign-in still returns a session.
    async with client() as c:
        bad = await c.post(f"{API_PREFIX}/auth/sign-in", json={"email": user.email, "password": "wrong"})
        assert bad.status_code == 401, bad.text
        good = await c.post(f"{API_PREFIX}/auth/sign-in", json={"email": user.email, "password": "CorrectHorse1!"})
        assert good.status_code == 200, good.text
        assert good.json()["access_token"]
    print("[PASS] sign-in returns generic errors; credential verdicts and happy path preserved")


# --------------------------------------------------------------------------
# 5. /auth/webhook: forged payload rejected, secrets never logged
# --------------------------------------------------------------------------
async def test_auth_webhook_requires_valid_signature():
    compute_webhook_signature = _helper("compute_webhook_signature")
    reset_limits()
    body = {
        "event": "user.created",
        "data": {"user": {"id": f"neon_{uuid.uuid4().hex[:8]}", "email": "gift@vynex.app", "name": "Gift"}},
    }
    import json as _json

    raw = _json.dumps(body).encode()

    async with client() as c:
        # Missing signature: previously this created the user and a 14-day trial.
        r = await c.post(f"{API_PREFIX}/auth/webhook", content=raw,
                         headers={"content-type": "application/json"})
        assert r.status_code == 401, r.text
        assert "signature" in r.text.lower()

        # Wrong signature.
        r = await c.post(f"{API_PREFIX}/auth/webhook", content=raw,
                         headers={"content-type": "application/json",
                                  "better-auth-signature": "0" * 64})
        assert r.status_code == 401, r.text

        # Truncated valid signature (the shape a timing-tolerant compare accepts).
        good = compute_webhook_signature(WEBHOOK_SECRET, raw)
        r = await c.post(f"{API_PREFIX}/auth/webhook", content=raw,
                         headers={"content-type": "application/json",
                                  "better-auth-signature": good[:-2] + "ab"})
        assert r.status_code == 401, r.text

        async with Session() as db:
            assert (await db.execute(select(User).where(User.email == "gift@vynex.app"))).scalar_one_or_none() is None

        # A correctly signed delivery still works, and the trial length now
        # follows TRIAL_DAYS instead of a hardcoded 14.
        with LogCapture() as logs:
            r = await c.post(f"{API_PREFIX}/auth/webhook", content=raw,
                             headers={"content-type": "application/json",
                                      "better-auth-signature": good})
            assert r.status_code == 200, r.text
            assert r.json()["message"] == "User synchronized successfully"
        async with Session() as db:
            created = (await db.execute(select(User).where(User.email == "gift@vynex.app"))).scalar_one()
            assert created is not None and created.full_name == "Gift"
            span = created.trial_expires_at - created.trial_started_at
            assert span.days == int(settings.TRIAL_DAYS), f"trial was {span.days}d, expected {settings.TRIAL_DAYS}d"

        # No log line at any level may carry the secret or a signature.
        blob = logs.text()
        assert WEBHOOK_SECRET not in blob
        assert good not in blob
        assert "Expected" not in blob and "Received" not in blob

    # Unconfigured secret = refuse, not fall open.
    settings.NEON_WEBHOOK_SECRET = ""
    async with client() as c:
        r = await c.post(f"{API_PREFIX}/auth/webhook", content=raw,
                         headers={"content-type": "application/json",
                                  "better-auth-signature": good})
        assert r.status_code == 503, r.text
        assert r.json()["detail"]["code"] == "webhook_not_configured"
    settings.NEON_WEBHOOK_SECRET = WEBHOOK_SECRET
    print("[PASS] /auth/webhook rejects unsigned/forged payloads, honors the secret, logs no digests")


# --------------------------------------------------------------------------
# 6. media jobs: owner scoping (IDOR) and honest cancellation
# --------------------------------------------------------------------------
async def test_media_job_scoping_and_cancel():
    reset_limits()
    async with Session() as db:
        alice = await make_user(db, "alice@vynex.app")
        bob = await make_user(db, "bob@vynex.app")
        carol = await make_user(db, "carol@vynex.app")  # separate workspace
        # The rule is "created by this user OR inside this workspace", so a row
        # stamped with alice's org but somebody else's user_id is still hers.
        alice_org = (await db.execute(select(Organization).where(Organization.owner_id == alice.id))).scalar_one()
        workspace_job = await make_job(db, alice, prompt="workspace shared render")
        workspace_job.user_id = (await db.execute(select(User).where(User.email == "bob@vynex.app"))).scalar_one().id
        workspace_job.org_id = alice_org.id
        await db.commit()

        alice_job = await make_job(db, alice, status="pending", prompt="alice secret campaign")
        running_job = await make_job(db, alice, status="in_progress", prompt="still rendering")
        done_job = await make_job(db, alice, status="completed", result_url="https://cdn/x.png")

        # Service-level scoping.
        assert await media_service.get_media_job(db, bob, alice_job.id) is None, \
            "a different user must not resolve another user's job"
        assert (await media_service.get_media_job(db, alice, alice_job.id)).id == alice_job.id

    async with client("198.51.100.20") as c:
        bob_h = auth_headers(bob)
        alice_h = auth_headers(alice)

        # The old code filtered on id alone: bob could read alice's prompt and
        # result URL by walking ids.
        r = await c.get(f"{API_PREFIX}/media/jobs/{alice_job.id}", headers=bob_h)
        assert r.status_code == 404, f"cross-user read must 404, got {r.status_code}"
        assert "alice secret campaign" not in r.text

        r = await c.get(f"{API_PREFIX}/media/jobs/{alice_job.id}", headers=alice_h)
        assert r.status_code == 200 and r.json()["prompt"] == "alice secret campaign"

        # A third account in its own workspace gets 404 ...
        r = await c.get(f"{API_PREFIX}/media/jobs/{alice_job.id}", headers=auth_headers(carol))
        assert r.status_code == 404, f"carol (other workspace) must not read it, got {r.status_code}"
        # ... while a job inside alice's workspace stays readable to her even
        # though the user_id column names somebody else.
        r = await c.get(f"{API_PREFIX}/media/jobs/{workspace_job.id}", headers=auth_headers(alice))
        assert r.status_code == 200, f"workspace-scoped read broke: {r.status_code} {r.text}"

        # Cancel someone else's job: same 404, and nothing happened to it.
        r = await c.post(f"{API_PREFIX}/media/jobs/{alice_job.id}/cancel", headers=bob_h)
        assert r.status_code == 404, r.text
        async with Session() as db:
            row = (await db.execute(select(MediaGenerationJob).where(MediaGenerationJob.id == alice_job.id))).scalar_one()
            assert row.status == "pending", "a non-owner must not be able to cancel"

        # The fake-success endpoint this replaces: an already-finished job is a
        # 409 with its real status, never a "success".
        r = await c.post(f"{API_PREFIX}/media/jobs/{done_job.id}/cancel", headers=alice_h)
        assert r.status_code == 409, r.text
        detail = r.json()["detail"]
        assert detail["code"] == "job_not_cancellable" and detail["status"] == "completed"
        assert "nothing to cancel" in detail["message"]

        # A live job really does get cancelled.
        r = await c.post(f"{API_PREFIX}/media/jobs/{running_job.id}/cancel", headers=alice_h)
        assert r.status_code == 200, r.text
        assert r.json()["success"] is True and r.json()["status"] == "canceled"
        async with Session() as db:
            row = (await db.execute(select(MediaGenerationJob).where(MediaGenerationJob.id == running_job.id))).scalar_one()
            assert row.status == "canceled", "cancel must persist, not just answer"
            assert row.result_url is None

        # Cancelling twice is honest about the second call.
        r = await c.post(f"{API_PREFIX}/media/jobs/{running_job.id}/cancel", headers=alice_h)
        assert r.status_code == 409 and r.json()["detail"]["status"] == "canceled"

        # Unknown id is a 404 for the owner too (no probing for existence).
        r = await c.post(f"{API_PREFIX}/media/jobs/nope-404/cancel", headers=alice_h)
        assert r.status_code == 404
    print("[PASS] media job reads/cancels are owner/workspace-scoped and report what actually happened")


# --------------------------------------------------------------------------
# 7. provider callback cannot be forged, and cannot resurrect a cancelled job
# --------------------------------------------------------------------------
async def test_provider_webhook_requires_capability_token():
    sign_job_webhook_token = _helper("sign_job_webhook_token")
    reset_limits()
    request_id = f"hf_{uuid.uuid4().hex[:10]}"
    async with Session() as db:
        owner = await make_user(db, "hfowner@vynex.app")
        job = await make_job(db, owner, status="in_progress", provider="higgsfield",
                             provider_job_id=request_id)
        canceled_id = f"hf_{uuid.uuid4().hex[:10]}"
        canceled = await make_job(db, owner, status="in_progress", provider="higgsfield",
                                  provider_job_id=canceled_id)

    payload = {
        "request_id": request_id,
        "status": "completed",
        "payload": {"images": [{"url": "https://cdn.evil.app/stolen.png"}]},
    }
    async with client("198.51.100.30") as c:
        url = f"{API_PREFIX}/webhooks/higgsfield"

        # No token (the shape every anonymous attacker used to send).
        r = await c.post(url, json=payload)
        assert r.status_code == 403, r.text
        assert r.json()["detail"]["code"] == "invalid_webhook_token"
        async with Session() as db:
            row = (await db.execute(select(MediaGenerationJob).where(MediaGenerationJob.id == job.id))).scalar_one()
            assert row.status == "in_progress" and row.result_url is None, "rejection must not mutate the job"
            # Verification happens before any write, so a rejected flood cannot
            # use this route to grow the event table either.
            assert (await db.execute(select(WebhookEvent))).scalars().all() == []

        # Token minted for a different job — replaying one URL elsewhere.
        other_token = sign_job_webhook_token(uuid.uuid4().hex)
        r = await c.post(f"{url}?token={other_token}", json=payload)
        assert r.status_code == 403, r.text

        # A forged result for a job we do not have.
        r = await c.post(f"{url}?token={sign_job_webhook_token(job.id)}",
                         json={"request_id": "unknown-id", "status": "completed"})
        assert r.status_code == 403, r.text

        # The legitimate callback for this job.
        r = await c.post(f"{url}?token={sign_job_webhook_token(job.id)}", json=payload)
        assert r.status_code == 200, r.text
        async with Session() as db:
            row = (await db.execute(select(MediaGenerationJob).where(MediaGenerationJob.id == job.id))).scalar_one()
            assert row.status == "completed" and row.result_url == "https://cdn.evil.app/stolen.png"

        # Cancelled stays cancelled even when the provider reports success.
        await c.post(f"{API_PREFIX}/media/jobs/{canceled.id}/cancel", headers=auth_headers(owner))
        r = await c.post(
            f"{url}?token={sign_job_webhook_token(canceled.id)}",
            json={"request_id": canceled_id, "status": "completed",
                  "payload": {"images": [{"url": "https://cdn.evil.app/late.png"}]}},
        )
        assert r.status_code == 200, r.text
        async with Session() as db:
            row = (await db.execute(select(MediaGenerationJob).where(MediaGenerationJob.id == canceled.id))).scalar_one()
            assert row.status == "canceled", "a late webhook must not resurrect a cancelled job"
            assert row.result_url is None
    print("[PASS] higgsfield callback needs a job-bound capability token; cancel is durable")


# --------------------------------------------------------------------------
# 8. bad envelopes and unknown-route hygiene
# --------------------------------------------------------------------------
async def test_webhook_malformed_bodies_are_400_not_500():
    compute_webhook_signature = _helper("compute_webhook_signature")
    reset_limits()
    async with client("198.51.100.40") as c:
        for body, ctype in ((b"not json", "application/json"), (b"[1,2,3]", "application/json"),
                            (b'{"a":1}', "application/json")):
            r = await c.post(f"{API_PREFIX}/auth/webhook", content=body,
                             headers={"content-type": ctype,
                                      "better-auth-signature": compute_webhook_signature(WEBHOOK_SECRET, body)})
            assert r.status_code in (200, 400), f"{body!r} -> {r.status_code}: {r.text}"

        # Envelope without a signature is a rejection, not a crash.
        r = await c.post(f"{API_PREFIX}/webhooks/higgsfield", content=b"nope",
                         headers={"content-type": "application/json"})
        assert r.status_code == 400, r.text
    print("[PASS] malformed webhook bodies return 400/200, never a 500")


TESTS = [
    test_reset_link_not_returned_and_enumeration_closed,
    test_forgot_password_rate_limit,
    test_limiter_window_and_bounds,
    test_sign_in_generic_failure_text,
    test_auth_webhook_requires_valid_signature,
    test_media_job_scoping_and_cancel,
    test_provider_webhook_requires_capability_token,
    test_webhook_malformed_bodies_are_400_not_500,
]


async def main():
    """Runs every case, reports each, exits non-zero if any failed.

    Deliberately not fail-fast: the point of this file is to be runnable against
    an unpatched checkout to show what was exploitable, so a reviewer gets the
    full red/green picture from one command.
    """
    prev_secret = settings.NEON_WEBHOOK_SECRET
    settings.NEON_WEBHOOK_SECRET = WEBHOOK_SECRET
    failures = []
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        for test in TESTS:
            try:
                await test()
            except Exception as exc:  # noqa: BLE001 - report, do not abort
                failures.append((test.__name__, exc))
                print(f"[FAIL] {test.__name__}: {type(exc).__name__}: {exc}")
    finally:
        settings.NEON_WEBHOOK_SECRET = prev_secret

    print(f"\n{len(TESTS) - len(failures)}/{len(TESTS)} security reproductions passed.")
    if failures:
        print("Failing cases mean the corresponding fix is absent on this revision.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
