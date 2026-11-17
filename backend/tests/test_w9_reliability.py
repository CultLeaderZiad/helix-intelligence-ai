"""W9 reliability: optional Sentry (off by default, scrubbed) and the
migration revision in /api/health. No database."""
from __future__ import annotations

import asyncio

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.api.routers import health
from app.core import error_reporting
from app.core.config import settings


def test_sentry_is_off_without_a_dsn(monkeypatch):
    monkeypatch.setattr(settings, "SENTRY_DSN", "")
    assert error_reporting.init_error_reporting() is False


def test_sentry_starts_without_pii_when_a_dsn_is_set(monkeypatch):
    import sentry_sdk

    seen = {}
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://key@o0.ingest.sentry.io/1")
    monkeypatch.setattr(sentry_sdk, "init", lambda **kw: seen.update(kw))
    assert error_reporting.init_error_reporting() is True
    assert seen["send_default_pii"] is False
    assert seen["traces_sample_rate"] == 0.0
    assert seen["before_send"] is error_reporting.before_send


def test_events_are_scrubbed_of_auth_cookies_bodies_and_emails():
    event = error_reporting.before_send({
        "message": "sign-in failed for someone@example.com",
        "user": {"id": "u1", "email": "someone@example.com", "ip_address": "1.2.3.4"},
        "request": {
            "headers": {"Authorization": "Bearer abc", "Cookie": "s=1", "X-Cron-Secret": "c", "Accept": "*/*"},
            "cookies": {"s": "1"},
            "data": {"password": "pw"},
        },
        "extra": {"access_token": "t", "note": "mail someone@example.com"},
    })
    assert event["message"] == "sign-in failed for [email]"
    assert event["user"] == {"id": "u1"}
    headers = event["request"]["headers"]
    assert headers["Authorization"] == headers["Cookie"] == headers["X-Cron-Secret"] == "[Filtered]"
    assert headers["Accept"] == "*/*"
    assert "cookies" not in event["request"] and "data" not in event["request"]
    assert event["extra"] == {"access_token": "[Filtered]", "note": "mail [email]"}


def _repo_head():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    heads = ScriptDirectory.from_config(cfg).get_heads()
    assert len(heads) == 1, heads
    return heads[0]


def test_health_reports_the_code_head_and_compares_it():
    head = _repo_head()
    assert health.code_alembic_head() == head
    assert health._migration_status(head) == {"database_revision": head, "code_head": head, "up_to_date": True}
    assert health._migration_status("0000old")["up_to_date"] is False
    assert health._migration_status(None) == {"database_revision": None, "code_head": head, "up_to_date": False}


def test_database_revision_reads_alembic_version_and_tolerates_its_absence():
    class _Result:
        def scalar_one_or_none(self):
            return "abc123"

    class _Session:
        def __init__(self, fail=False):
            self.fail, self.rolled_back = fail, False

        async def execute(self, statement):
            assert "alembic_version" in str(statement)
            if self.fail:
                raise RuntimeError("no table")
            return _Result()

        async def rollback(self):
            self.rolled_back = True

    assert asyncio.run(health._database_revision(_Session())) == "abc123"
    broken = _Session(fail=True)
    assert asyncio.run(health._database_revision(broken)) is None and broken.rolled_back
