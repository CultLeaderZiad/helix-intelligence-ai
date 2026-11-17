"""The sign-up trial follows the docs: off unless SIGNUP_TRIAL_DAYS is set.

README and API_CONTRACTS ("Access model") say access is granted by an admin
and there is no trial. No database: the trial helper returns before any
query when the flag is 0.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.core.config import settings
from app.services import auth_service

BACKEND = Path(__file__).resolve().parents[1]


def test_default_is_no_trial_when_the_env_var_is_unset():
    env = {k: v for k, v in os.environ.items() if k != "SIGNUP_TRIAL_DAYS"}
    env.setdefault("SECRET_KEY", "test_secret_not_real_0123456789abcdef")
    out = subprocess.run(
        [sys.executable, "-c", "from app.core.config import settings; print(settings.SIGNUP_TRIAL_DAYS)"],
        cwd=BACKEND, env=env, capture_output=True, text=True, check=True,
    )
    assert out.stdout.strip() == "0"


def test_env_var_turns_the_trial_on():
    env = dict(os.environ, SIGNUP_TRIAL_DAYS="7")
    env.setdefault("SECRET_KEY", "test_secret_not_real_0123456789abcdef")
    out = subprocess.run(
        [sys.executable, "-c", "from app.core.config import settings; print(settings.SIGNUP_TRIAL_DAYS)"],
        cwd=BACKEND, env=env, capture_output=True, text=True, check=True,
    )
    assert out.stdout.strip() == "7"


@pytest.mark.signup_trial
def test_no_grant_is_written_when_the_trial_is_off(monkeypatch):
    monkeypatch.setattr(settings, "SIGNUP_TRIAL_DAYS", 0)

    class _NoDb:
        def __getattr__(self, name):
            raise AssertionError(f"trial helper touched the database ({name}) with the trial off")

    user = type("U", (), {"id": "u1", "trial_started_at": None, "trial_expires_at": None})()
    asyncio.run(auth_service._start_signup_trial(_NoDb(), user, object()))
    assert user.trial_started_at is None and user.trial_expires_at is None
