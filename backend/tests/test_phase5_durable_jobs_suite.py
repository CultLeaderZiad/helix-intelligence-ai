"""Phase 5 Test Suite: Durable Jobs, Worker Lifecycle, Reconciliation & Privacy.

Tests cover:
- F23: SSRF IPv4-mapped IPv6 and hop-by-hop redirect safety in security_service & leadgen_pipeline
- F24: Database session engine isolation with NullPool in workers, long-lived loop avoiding closed loop errors
- F25: Durable worker heartbeat & boot ID tracking in scout_jobs, scout_maps_jobs, media_jobs; sweeping & refund
- F26: Live worker health verification in _is_worker_available(db)
- F69: Clean RFC 3339 UTC ISO timestamps without invalid +00:00Z dual-offsets in team_service & updates
- F71: Attribution PII sanitization in auth_service (email strings dropped, referrer URL queries stripped, email not logged)
- F72: UTM persistence logic supporting term/content-only attribution
- F73: Accessibility contracts: focus trap/containment in ConfirmDialog, keyboard reveal in Field, htmlFor/id in SavedDraftsModal
"""
from __future__ import annotations

import asyncio
import datetime
from datetime import timezone
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.db.session import worker_session_maker, worker_engine
from app.models.user import User
from app.models.leadgen import LeadGenJob, LeadGenWorkerHeartbeat
from app.models.scout import ScoutJob, ScoutMapsJob
from app.models.media_job import MediaGenerationJob
from app.schemas.auth import UserCreate
from app.services.security_service import is_ip_blocked, is_safe_public_url, safe_http_get
from app.services.leadgen_pipeline import _is_private_host as pipe_is_private_host
from app.services.job_reconciliation import _sweep_table, reconcile_once
from app.services.team_service import _format_utc_iso
from app.services.auth_service import register_user
from app.api.routers.updates import normalize_to_utc
from app.api.routers.leadgen import _is_worker_available
from sqlalchemy.pool import NullPool

REPO_ROOT = Path(__file__).resolve().parents[2]


class MockResult:
    """Mock query result supporting scalar, scalar_one_or_none, and scalars()."""
    def __init__(self, item=None, items=None):
        self._item = item
        self._items = items or ([] if item is None else [item])

    def scalar_one_or_none(self):
        return self._item

    def scalar(self):
        return self._item

    def scalars(self):
        m = MagicMock()
        m.all = MagicMock(return_value=self._items)
        return m


# ==============================================================================
# 1. F23: SSRF IPv4-Mapped IPv6 & Redirect Validation
# ==============================================================================

def test_f23_ssrf_ipv4_mapped_ipv6_and_private_host_blocking():
    """Verify that IPv4-mapped IPv6 addresses (e.g. ::ffff:127.0.0.1) and private CIDRs are blocked."""
    import ipaddress
    blocked_ips = [
        "::ffff:127.0.0.1",
        "::ffff:10.0.0.1",
        "::ffff:172.16.0.1",
        "::ffff:192.168.1.1",
        "::ffff:169.254.169.254",
        "::ffff:0.0.0.0",
        "127.0.0.1",
        "169.254.169.254",
        "10.254.0.1",
        "192.168.0.100",
        "::1",
        "0.0.0.0",
    ]
    for ip_str in blocked_ips:
        ip_obj = ipaddress.ip_address(ip_str)
        assert is_ip_blocked(ip_obj) is True, f"security_service is_ip_blocked failed for {ip_str}"
        assert pipe_is_private_host(ip_str) is True, f"leadgen_pipeline failed to block {ip_str}"
        assert is_safe_public_url(f"http://{ip_str}/path") is False

    assert pipe_is_private_host("localhost") is True
    assert is_safe_public_url("http://localhost:8000/api") is False

    # Public hosts must be permitted
    allowed_ips = ["8.8.8.8", "1.1.1.1"]
    for ip_str in allowed_ips:
        ip_obj = ipaddress.ip_address(ip_str)
        assert is_ip_blocked(ip_obj) is False, f"security_service blocked legitimate {ip_str}"
        assert pipe_is_private_host(ip_str) is False, f"leadgen_pipeline blocked legitimate {ip_str}"
        assert is_safe_public_url(f"https://{ip_str}/api") is True


def test_f23_safe_http_get_hop_by_hop_redirect_safety():
    """Verify safe_http_get blocks redirects that target private / internal IP ranges."""
    with patch("httpx.get") as mock_httpx_get:
        # Mock initial redirect pointing to private metadata endpoint
        mock_resp = MagicMock()
        mock_resp.is_redirect = True
        mock_resp.headers = {"location": "http://169.254.169.254/latest/meta-data/"}
        mock_httpx_get.return_value = mock_resp

        with pytest.raises(ValueError, match="SSRF blocked"):
            safe_http_get("https://example.com/redirect")


# ==============================================================================
# 2. F24: Worker Engine NullPool & Event Loop Re-entrancy
# ==============================================================================

def test_f24_worker_engine_uses_nullpool():
    """Verify worker_engine is configured with NullPool to prevent asyncpg loop reuse crashes."""
    assert isinstance(worker_engine.pool, NullPool), "worker_engine must use NullPool"
    assert worker_session_maker.kw["bind"] is worker_engine


# ==============================================================================
# 3. F25: Durable Worker Heartbeat Tracking & Job Sweep
# ==============================================================================

@pytest.mark.asyncio
async def test_f25_reconciliation_sweeper_handles_all_job_types():
    """Verify reconcile_once sweeps stalled jobs across discover, media, scout, maps, and leadgen."""
    with patch("app.services.job_reconciliation._sweep_table") as mock_sweep, \
         patch("app.services.job_reconciliation._sweep_unrefunded_failed_jobs", return_value=[]), \
         patch("app.services.job_reconciliation.refund", new_callable=AsyncMock) as mock_refund, \
         patch("app.services.job_reconciliation.worker_session_maker") as session_factory, \
         patch("app.services.job_reconciliation._sweep_monitor_runs", return_value=0), \
         patch("app.services.work_outbox.requeue_expired_leases", return_value=0):

        session = session_factory.return_value.__aenter__.return_value
        result = MagicMock()
        result.mappings.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result)

        # Mock rows returned for each table
        mock_sweep.side_effect = [
            [{"id": "disc-1", "org_id": "org-1"}],                          # scrape_jobs
            [{"id": "media-1"}],                                            # media_jobs
            [{"id": "scout-1", "org_id": "org-2", "credits_used": 5.0}],    # scout_jobs
            [{"id": "maps-1", "org_id": "org-3", "credits_used": 3.0}],     # scout_maps_jobs
            [{"id": "lead-1", "org_id": "org-4", "credits_used": 4.0}],     # leadgen_jobs
        ]

        swept = await reconcile_once()

        assert swept.get("discover") == 1
        assert swept.get("media") == 1
        assert swept.get("scout") == 1
        assert swept.get("maps") == 1
        assert swept.get("leadgen") == 1
        assert swept.get("refunded", 0) >= 4  # discover + scout + maps + leadgen refunded!
        assert mock_refund.call_count >= 4


# ==============================================================================
# 4. F26: Live Worker Health Verification
# ==============================================================================

@pytest.mark.asyncio
async def test_f26_live_worker_health_verification():
    """Verify _is_worker_available checks live heartbeat and rejects when worker is dead."""
    db = AsyncMock()

    # Case 1: Disabled worker -> unavailable
    with patch.object(settings, "SCRAPLING_INLINE_WORKER", False), \
         patch.object(settings, "SCRAPLING_WORKER_ENABLED", False), \
         patch.object(settings, "SCRAPLING_WORKER_URL", ""):
        db.execute.return_value = MockResult(item=None)
        is_avail = await _is_worker_available(db)
        assert is_avail is False

    # Case 2: Worker enabled, remote URL empty, fresh heartbeat -> available
    with patch.object(settings, "SCRAPLING_INLINE_WORKER", False), \
         patch.object(settings, "SCRAPLING_WORKER_ENABLED", True), \
         patch.object(settings, "SCRAPLING_WORKER_URL", ""):
        fresh_hb = LeadGenWorkerHeartbeat(
            id="scrapling_worker",
            updated_at=datetime.datetime.now(timezone.utc),
            browsers_ready=True,
        )
        db.execute.return_value = MockResult(item=fresh_hb)
        is_avail = await _is_worker_available(db)
        assert is_avail is True

        # Case 3: Heartbeat is stale (older than fresh window) -> unavailable
        stale_hb = LeadGenWorkerHeartbeat(
            id="scrapling_worker",
            updated_at=datetime.datetime.now(timezone.utc) - datetime.timedelta(minutes=10),
            browsers_ready=True,
        )
        db.execute.return_value = MockResult(item=stale_hb)
        is_avail = await _is_worker_available(db)
        assert is_avail is False


# ==============================================================================
# 5. F69: Clean RFC 3339 UTC ISO Timestamps (No +00:00Z)
# ==============================================================================

def test_f69_format_utc_iso_no_double_offset():
    """Verify _format_utc_iso formats ISO timestamps with Z and never produces +00:00Z."""
    # Aware datetime with +00:00
    dt_aware_utc = datetime.datetime(2026, 10, 5, 12, 30, 45, tzinfo=timezone.utc)
    res = _format_utc_iso(dt_aware_utc)
    assert res == "2026-10-05T12:30:45Z"
    assert "+00:00" not in res
    assert not res.endswith("+00:00Z")

    # Aware datetime with non-UTC offset (e.g. +03:00)
    tz_plus_3 = timezone(datetime.timedelta(hours=3))
    dt_aware_plus3 = datetime.datetime(2026, 10, 5, 15, 30, 45, tzinfo=tz_plus_3)
    res = _format_utc_iso(dt_aware_plus3)
    # 15:30 +03:00 is 12:30 UTC
    assert res == "2026-10-05T12:30:45Z"

    # Naive datetime is treated as UTC
    dt_naive = datetime.datetime(2026, 10, 5, 12, 30, 45)
    res = _format_utc_iso(dt_naive)
    assert res == "2026-10-05T12:30:45Z"


def test_f69_normalize_to_utc_preserves_timestamp():
    """Verify normalize_to_utc correctly converts aware timestamps instead of naive strip."""
    tz_plus_2 = timezone(datetime.timedelta(hours=2))
    aware_dt = datetime.datetime(2026, 10, 5, 14, 0, 0, tzinfo=tz_plus_2)

    converted = normalize_to_utc(aware_dt)
    assert converted.tzinfo == timezone.utc
    assert converted.hour == 12  # 14:00+02:00 -> 12:00 UTC


# ==============================================================================
# 6. F71 & F72: Attribution PII Sanitization & Term/Content Persistence
# ==============================================================================

@pytest.mark.asyncio
async def test_f71_register_user_sanitizes_pii_from_attribution():
    """Verify register_user drops email addresses from UTMs and strips query from referrer."""
    db = AsyncMock()
    db.execute.return_value = MockResult(item=None)  # No existing user
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    captured_user = None

    def add_side_effect(instance):
        nonlocal captured_user
        if isinstance(instance, User):
            captured_user = instance

    db.add = MagicMock(side_effect=add_side_effect)

    user_in = UserCreate(
        name="Privacy User",
        email="test_clean@example.com",
        password="ValidPassword123!",
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="victim@example.com",  # PII in campaign!
        utm_term="targeted_kw",
        utm_content="secret_ad",
        referrer="https://partner.com/welcome?token=s3cr3t&user_email=leak@domain.com",  # Query params!
    )

    with patch.object(settings, "USE_MOCKS", False), \
         patch("app.services.auth_service.logger.info") as mock_logger:
        await register_user(db, user_in)

        assert captured_user is not None
        metadata = captured_user.signup_metadata

        # F71: utm_campaign with email must be stripped!
        assert "utm_campaign" not in metadata
        assert metadata.get("utm_source") == "google"
        assert metadata.get("utm_medium") == "cpc"
        assert metadata.get("utm_term") == "targeted_kw"
        assert metadata.get("utm_content") == "secret_ad"

        # Referrer query parameters and fragments must be stripped!
        assert metadata.get("referrer") == "https://partner.com/welcome"

        # Logger must not log plain email alongside metadata
        for call_args in mock_logger.call_args_list:
            log_str = str(call_args)
            assert "test_clean@example.com" not in log_str


def test_f72_utm_file_verifies_term_content_condition():
    """Verify src/lib/utm.js persists attribution when only utm_term or utm_content are provided."""
    utm_path = REPO_ROOT / "src" / "lib" / "utm.js"
    content = utm_path.read_text(encoding="utf-8")
    assert "utmTerm || utmContent" in content
    assert "EMAIL_REGEX" in content


# ==============================================================================
# 7. F73: Accessibility Contracts
# ==============================================================================

def test_f73_accessibility_contracts_in_components():
    """Verify ConfirmDialog focus trap, Field password button access, and SavedDraftsModal labels."""
    confirm_dialog_path = REPO_ROOT / "src" / "components" / "ui" / "ConfirmDialog.jsx"
    confirm_content = confirm_dialog_path.read_text(encoding="utf-8")
    assert "previouslyFocusedRef" in confirm_content
    assert "dialogRef" in confirm_content
    assert "shiftKey" in confirm_content

    field_path = REPO_ROOT / "src" / "components" / "ui" / "Field.jsx"
    field_content = field_path.read_text(encoding="utf-8")
    assert 'tabIndex={-1}' not in field_content

    drafts_modal_path = REPO_ROOT / "src" / "components" / "SavedDraftsModal.jsx"
    drafts_content = drafts_modal_path.read_text(encoding="utf-8")
    assert 'htmlFor="draft-title-input"' in drafts_content
    assert 'id="draft-title-input"' in drafts_content
    assert 'htmlFor="draft-target-input"' in drafts_content
    assert 'id="draft-target-input"' in drafts_content
    assert 'htmlFor="draft-notes-input"' in drafts_content
    assert 'id="draft-notes-input"' in drafts_content
