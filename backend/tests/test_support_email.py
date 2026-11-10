"""SUPPORT_EMAIL is the reply-to and the footer on every transactional send."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import DEFAULT_SUPPORT_EMAIL, Settings, validate_boot_invariants
from app.services import email_service
from app.services.email_service import send_email


def test_support_email_defaults_to_the_published_address(monkeypatch):
    monkeypatch.delenv("SUPPORT_EMAIL", raising=False)
    cfg = Settings(
        ENVIRONMENT="test",
        SECRET_KEY="s" * 40,
        DATABASE_URL="postgresql+asyncpg://test:test@127.0.0.1:5432/helix",
        PUBLIC_APP_BASE_URL="http://localhost:3000",
        PUBLIC_API_BASE_URL="/api",
        APP_BASE_URL="http://localhost:3000",
        BACKEND_CORS_ORIGINS="http://localhost:3000",
    )
    assert cfg.SUPPORT_EMAIL == DEFAULT_SUPPORT_EMAIL == "support@cyreax.com"


def test_invalid_support_email_refuses_boot():
    with pytest.raises(RuntimeError, match="SUPPORT_EMAIL"):
        validate_boot_invariants(type("Cfg", (), {
            "ENVIRONMENT": "development",
            "SUPPORT_EMAIL": "not-an-email",
            "PUBLIC_APP_BASE_URL": "http://localhost:3000",
            "PUBLIC_API_BASE_URL": "/api",
            "APP_BASE_URL": "http://localhost:3000",
            "R2_PUBLIC_BASE_URL": "",
            "R2_ENDPOINT_URL": "",
            "DATABASE_URL": "postgresql+asyncpg://test:test@127.0.0.1:5432/helix",
            "BACKEND_CORS_ORIGINS": "",
            "BACKEND_CORS_ORIGIN_REGEX": "",
            "HELIX_DISPATCH_INLINE": False,
            "AUTH_DEV_RESET_RETURN": False,
        })())


def test_mailer_does_not_hardcode_the_sender_or_the_support_address():
    source = Path(email_service.__file__).read_text(encoding="utf-8")
    assert "noreply@" not in source
    assert "support@cyreax.com" not in source
    assert "reply_to" in source


@pytest.mark.asyncio
async def test_send_email_sets_reply_to_and_support_footer(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"id": "email_1"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json, headers):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(email_service.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(email_service.settings, "RESEND_API_KEY", "re_test")
    monkeypatch.setattr(email_service.settings, "RESEND_FROM", "Helix <sender@example.invalid>")
    monkeypatch.setattr(email_service.settings, "SUPPORT_EMAIL", "support@cyreax.com")

    result = await send_email(
        to="person@example.invalid",
        subject="Reset your Helix Intelligence password",
        html="<p>Hello</p>",
        text="Hello",
    )

    assert result.accepted is True
    body = captured["json"]
    assert body["from"] == "Helix <sender@example.invalid>"
    assert body["reply_to"] == "support@cyreax.com"
    assert body["html"].count("mailto:support@cyreax.com") == 1
    assert "support@cyreax.com" in body["text"]
    assert "sender@example.invalid" not in body["html"]


@pytest.mark.asyncio
async def test_support_footer_is_not_duplicated(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"id": "email_2"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json, headers):
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(email_service.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(email_service.settings, "RESEND_API_KEY", "re_test")
    monkeypatch.setattr(email_service.settings, "RESEND_FROM", "Helix <sender@example.invalid>")
    monkeypatch.setattr(email_service.settings, "SUPPORT_EMAIL", "help@example.invalid")

    html = '<p>Invite</p><p><a href="mailto:help@example.invalid">help@example.invalid</a></p>'
    await send_email(to="person@example.invalid", subject="Invitation", html=html, text="Write to help@example.invalid")
    body = captured["json"]
    assert body["reply_to"] == "help@example.invalid"
    assert body["html"].count("mailto:help@example.invalid") == 1
    assert body["text"].count("help@example.invalid") == 1
