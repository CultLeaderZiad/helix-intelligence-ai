"""Same-second password reset must revoke the old session and accept the new one."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.deps import authenticate_bearer, session_is_revoked
from app.core.security import create_access_token, verify_neon_token


SECOND = 1_792_352_388


def _at(offset: float) -> datetime:
    return datetime.fromtimestamp(SECOND + offset, timezone.utc)


def _freeze(moment: datetime):
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return moment

    return Frozen


class _DB:
    def __init__(self, user):
        self.user = user

    async def execute(self, _stmt):
        user = self.user
        return SimpleNamespace(scalar_one_or_none=lambda: user)


@pytest.mark.asyncio
async def test_same_second_reset_rejects_old_token_and_accepts_new_sign_in(monkeypatch):
    """A token minted before the reset in this UTC second stays revoked.

    The sign-in minted after the reset, still inside that second, is accepted.
    JWT iat is the whole second for both tokens. token_version tells them apart.
    """
    monkeypatch.setattr("app.core.security.datetime", _freeze(_at(0.2)))
    before = create_access_token("usr_same_second", token_version=1)
    monkeypatch.setattr("app.core.security.datetime", _freeze(_at(0.8)))
    after = create_access_token("usr_same_second", token_version=2)
    monkeypatch.setattr("app.core.security.datetime", _freeze(_at(-0.2)))
    previous_second = create_access_token("usr_same_second", token_version=2)

    before_payload = await verify_neon_token(before)
    after_payload = await verify_neon_token(after)
    previous_payload = await verify_neon_token(previous_second)
    assert before_payload["iat"] == SECOND
    assert after_payload["iat"] == SECOND
    assert before_payload["ver"] == 1
    assert after_payload["ver"] == 2
    assert previous_payload["iat"] == SECOND - 1

    user = SimpleNamespace(
        id="usr_same_second",
        is_banned=False,
        is_suspended=False,
        signup_metadata={
            "token_version": 2,
            "sessions_revoked_at": _at(0.4).isoformat(),
        },
    )
    assert session_is_revoked(user, before_payload)
    assert not session_is_revoked(user, after_payload)
    assert session_is_revoked(user, previous_payload)

    accepted = await authenticate_bearer(_DB(user), after)
    assert accepted.id == "usr_same_second"
    with pytest.raises(HTTPException) as old_session:
        await authenticate_bearer(_DB(user), before)
    assert old_session.value.status_code == 401
    assert old_session.value.detail["code"] == "session_revoked"


def test_external_session_still_uses_the_full_revocation_timestamp():
    user = SimpleNamespace(signup_metadata={
        "sessions_revoked_at": _at(0.4).isoformat(),
    })
    assert session_is_revoked(user, {"_token_class": "external", "iat": SECOND})
    assert not session_is_revoked(user, {"_token_class": "external", "iat": SECOND + 1})
