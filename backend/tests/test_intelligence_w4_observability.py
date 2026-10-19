"""Payload-free errors and safe diagnostic entry points; no live services."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, Response

from app.api.routers import auth, health
from app.services.ai.base import AIProvider


@pytest.mark.asyncio
async def test_readiness_does_not_disclose_database_exception(monkeypatch, caplog):
    def unavailable():
        raise RuntimeError("postgresql://user:CANARY_SECRET@private/db")

    monkeypatch.setattr(health, "async_session_maker", unavailable)
    response = Response()
    result = await health.readiness(response)
    assert response.status_code == 503
    assert "CANARY_SECRET" not in str(result)
    assert "CANARY_SECRET" not in caplog.text
    assert result["code"] == "database_unavailable"


@pytest.mark.asyncio
async def test_ai_provider_failure_is_sanitized():
    class BrokenProvider(AIProvider):
        async def _call_api(self, messages):
            raise RuntimeError("CANARY_PROVIDER_KEY prompt customer data")

    with pytest.raises(HTTPException) as caught:
        await BrokenProvider().generate_insight(SimpleNamespace(
            id="creative-id", headline="Synthetic", body="Synthetic copy",
            format="image", platform="meta", cta=None, days_active=1,
        ))
    assert caught.value.status_code == 503
    assert caught.value.detail == "AI insight generation is temporarily unavailable."
    assert caught.value.headers["X-Error-Code"] == "analysis_unavailable"
    assert "CANARY_PROVIDER_KEY" not in str(caught.value.detail)


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["insight", "patterns", "simulation"])
async def test_provider_http_failures_never_echo_upstream_payload(operation, caplog):
    class BrokenProvider(AIProvider):
        async def _call_api(self, messages):
            raise HTTPException(status_code=502, detail="CANARY_API_KEY private prompt")

    provider = BrokenProvider()
    creative = SimpleNamespace(id="creative-1", headline="Synthetic", body="Copy",
                               platform="meta", format="image", cta=None, days_active=1)
    call = {"insight": lambda: provider.generate_insight(creative),
            "patterns": lambda: provider.generate_patterns([creative]),
            "simulation": lambda: provider.simulate_audience_reactions(creative, [])}[operation]
    with pytest.raises(HTTPException) as caught:
        await call()
    assert caught.value.status_code == 503
    assert "CANARY" not in str(caught.value.detail)
    assert "CANARY" not in caplog.text


@pytest.mark.asyncio
async def test_logout_revocation_failure_is_not_success(monkeypatch, caplog):
    from app.core import security

    monkeypatch.setattr(security, "verify_neon_token", AsyncMock(return_value={"sub": "actor-1"}))
    db = SimpleNamespace(execute=AsyncMock(side_effect=RuntimeError("CANARY_DB_PASSWORD")))
    with pytest.raises(HTTPException) as caught:
        await auth.signout(db=db, token="CANARY_BEARER")
    assert caught.value.status_code == 503
    assert caught.value.detail["code"] == "session_revocation_unavailable"
    assert "CANARY" not in caplog.text


def test_meta_diagnostic_can_be_imported_without_token(monkeypatch, capsys):
    monkeypatch.delenv("META_ACCESS_TOKEN", raising=False)
    path = Path(__file__).parents[1] / "scripts/test_new_meta.py"
    spec = importlib.util.spec_from_file_location("w4_meta_diagnostic", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert capsys.readouterr().out == ""
    assert callable(module.main)


def test_structured_events_only_keep_allowlisted_identifiers(caplog):
    import logging
    from app.core.observability import log_event, request_id_context

    token = request_id_context.set("request-1")
    try:
        log_event(logging.getLogger("w4-test"), "provider_failed",
                  error=RuntimeError("CANARY_TOKEN prompt customer@example.invalid"),
                  actor_id="actor-1", tenant_id="tenant-1", job_id="job-1")
        log_event(logging.getLogger("w4-test"), "url_blocked", actor_id="email@example.invalid\nINJECTED")
    finally:
        request_id_context.reset(token)
    event = caplog.records[-2]
    assert (event.request_id, event.actor_id, event.tenant_id, event.job_id) == (
        "request-1", "actor-1", "tenant-1", "job-1")
    assert event.error_type == "RuntimeError"
    assert caplog.records[-1].actor_id is None
    assert "CANARY" not in caplog.text
    assert "example.invalid" not in caplog.text
    assert "INJECTED" not in caplog.text
    assert event.exc_info is None


@pytest.mark.asyncio
async def test_request_boundary_returns_safe_error_and_correlation(caplog):
    import asyncio
    import httpx
    from fastapi import FastAPI
    from app.main import add_security_headers

    isolated_app = FastAPI()
    isolated_app.middleware("http")(add_security_headers)

    @isolated_app.get("/explode")
    async def explode():
        raise RuntimeError("CANARY_JWT CANARY_DB_PASSWORD customer@example.invalid")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=isolated_app), base_url="http://local") as client:
        results = await asyncio.gather(*[
            client.get("/explode", headers={"X-Request-ID": "CANARY_USER_INPUT"}) for _ in range(2)
        ])
    assert all(result.status_code == 500 for result in results)
    ids = {result.headers["x-request-id"] for result in results}
    assert len(ids) == 2
    for result in results:
        assert result.json()["detail"]["code"] == "internal_error"
        assert result.json()["detail"]["request_id"] == result.headers["x-request-id"]
        assert "CANARY" not in result.text
        assert result.headers["x-content-type-options"] == "nosniff"
    assert {record.request_id for record in caplog.records if getattr(record, "event", None) == "request_failed"} == ids
    assert "CANARY" not in caplog.text


@pytest.mark.asyncio
async def test_health_diagnostics_do_not_accept_signing_key(monkeypatch):
    monkeypatch.setattr(health.settings, "HEALTH_DIAGNOSTIC_KEY", "synthetic-diagnostic-only")
    monkeypatch.setattr(health, "async_session_maker", lambda: (_ for _ in ()).throw(RuntimeError("CANARY_PASSWORD")))
    for credential in (health.settings.SECRET_KEY, "non-ascii-λ"):
        result = await health.health_check(Response(), x_admin_secret=credential)
        assert "env_vars" not in result
        assert "db_detail" not in result
    result = await health.health_check(Response(), x_admin_secret="synthetic-diagnostic-only")
    assert "env_vars" in result
    assert result["db_detail"] == "Database is unavailable"


def _load_runtime_probe():
    path = Path(__file__).parents[2] / "helix-audit/probes/runtime-probes.py"
    spec = importlib.util.spec_from_file_location("w4_runtime_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("url", [
    "postgresql://localhost/production", "postgresql://remote.example/helix_w4_probe_unique",
    "postgresql://localhost/helix_w4_probe_", "sqlite:///helix_w4_probe_unique",
    "postgresql://localhost/helix_w4_probe_unique?host=remote.example",
])
def test_runtime_probes_refuse_non_disposable_targets(monkeypatch, url):
    monkeypatch.setenv("HELIX_ALLOW_DISPOSABLE_PROBES", "yes")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(RuntimeError, match="local helix_w4_probe"):
        _load_runtime_probe().require_disposable_database()


def test_runtime_probes_require_explicit_opt_in_and_test_environment(monkeypatch):
    probe = _load_runtime_probe()
    monkeypatch.delenv("HELIX_ALLOW_DISPOSABLE_PROBES", raising=False)
    with pytest.raises(RuntimeError, match="HELIX_ALLOW_DISPOSABLE_PROBES"):
        probe.require_disposable_database()
    monkeypatch.setenv("HELIX_ALLOW_DISPOSABLE_PROBES", "yes")
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="ENVIRONMENT=test"):
        probe.require_disposable_database()
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/helix_w4_probe_unique")
    probe.require_disposable_database()
